# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2018, Arm Limited and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
import functools
from collections.abc import Mapping

from lisa.utils import HideExekallID, group_by_value
from lisa.conf import (
    DeferredValue, IntIntDict, IntListList, IntIntListDict, IntStrDict,
    MultiSrcConf, KeyDesc, LevelKeyDesc, TopLevelKeyDesc, DerivedKeyDesc
)
from lisa.energy_model import EnergyModel
from lisa.wlgen.rta import RTA

from devlib.target import KernelVersion, TypedKernelConfig
from devlib.exception import TargetStableError


def compute_capa_classes(conf):
    """
    Derive the platform's capacity classes from the given conf

    This is intended for the creation of the ``capacity-classes`` key of
    :class:`PlatformInfo`.
    """
    return list(group_by_value(conf['cpu-capacities']).values())


class KernelConfigKeyDesc(KeyDesc):
    def pretty_format(self, v):
        return '<kernel config>'


class KernelSymbolsAddress(KeyDesc):
    def pretty_format(self, v):
        return '<symbols address>'


class PlatformInfo(MultiSrcConf, HideExekallID):
    """
    Platform-specific information made available to tests.

    {generated_help}

    """

    # we could use mypy.subtypes.is_subtype and use the infrastructure provided
    # by typing module, but adding an external dependency is overkill for what
    # we need.
    STRUCTURE = TopLevelKeyDesc('platform-info', 'Platform-specific information', (
        LevelKeyDesc('rtapp', 'RTapp configuration', (
            KeyDesc('calib', 'RTapp calibration dictionary', [IntIntDict]),
        )),

        LevelKeyDesc('kernel', 'Kernel-related information', (
            KeyDesc('version', '', [KernelVersion]),
            KernelConfigKeyDesc('config', '', [TypedKernelConfig]),
            KernelSymbolsAddress('symbols-address', 'Dictionary of addresses to symbol names extracted from /proc/kallsyms', [IntStrDict]),
        )),
        KeyDesc('nrg-model', 'Energy model object', [EnergyModel]),
        KeyDesc('cpu-capacities', 'Dictionary of CPU ID to capacity value', [IntIntDict]),
        KeyDesc('abi', 'ABI, e.g. "arm64"', [str]),
        KeyDesc('os', 'OS being used, e.g. "linux"', [str]),
        KeyDesc('name', 'Free-form name of the board', [str]),
        KeyDesc('cpus-count', 'Number of CPUs', [int]),

        KeyDesc('freq-domains',
                'Frequency domains modeled by a list of CPU IDs for each domain',
                [IntListList]),
        KeyDesc('freqs', 'Dictionnary of CPU ID to list of frequencies', [IntIntListDict]),

        DerivedKeyDesc('capacity-classes',
                       'Capacity classes modeled by a list of CPU IDs for each '
                       'capacity, sorted by capacity',
                       [IntListList],
                       [['cpu-capacities']], compute_capa_classes),
    ))
    """Some keys have a reserved meaning with an associated type."""

    def add_target_src(self, target, rta_calib_res_dir, src='target', only_missing=True, **kwargs):
        """
        Add source from a live :class:`lisa.target.Target`.

        :param target: Target to inspect.
        :type target: lisa.target.Target

        :param rta_calib_res_dir: Result directory for rt-app calibrations.
        :type rta_calib_res_dir: str

        :param src: Named of the added source.
        :type src: str

        :param only_missing: If ``True``, only add values for the keys that are
            not already provided by another source. This allows speeding up the
            connection to target, at the expense of not being able to spot
            inconsistencies between user-provided values and autodetected values.
        :type only_missing: bool

        :Variable keyword arguments: Forwarded to
            :class:`lisa.conf.MultiSrcConf.add_src`.
        """
        info = {
            'nrg-model': lambda: self._nrg_model_from_target(target),
            'kernel': {
                'version': lambda: target.kernel_version,
                'config': lambda: target.config.typed_config,
            },
            'abi': lambda: target.abi,
            'os': lambda: target.os,
            'rtapp': {
                # Since it is expensive to compute, use an on-demand DeferredValue
                'calib': lambda: DeferredValue(RTA.get_cpu_calibrations, target, rta_calib_res_dir)
            },
            'cpus-count': lambda: target.number_of_cpus
        }

        def get_freq_domains():
            if target.is_module_available('cpufreq'):
                return list(target.cpufreq.iter_domains())
            else:
                return None

        info['freq-domains'] = get_freq_domains

        def get_freqs():
            if target.is_module_available('cpufreq'):
                freqs = {cpu: target.cpufreq.list_frequencies(cpu)
                        for cpu in range(target.number_of_cpus)}
                # Only add the frequency info if there is any, otherwise don't
                # mislead the client code with empty frequency list
                if all(freqs.values()):
                    return freqs
                else:
                    return None
            else:
                return None

        info['freqs'] = get_freqs

        def get_cpu_capacities():
            if target.is_module_available('sched'):
                return target.sched.get_capacities(default=1024)
            else:
                return None

        info['cpu-capacities'] = get_cpu_capacities

        info['kernel']['symbols-address'] = functools.partial(self._read_kallsyms, target)

        def dfs(existing_info, new_info):
            def evaluate(existing_info, key, val):
                if isinstance(val, Mapping):
                    return dfs(existing_info[key], val)
                else:
                    if only_missing and key in existing_info:
                        return None
                    else:
                        return val()

            return {
                key: evaluate(existing_info, key, val)
                for key, val in new_info.items()
            }

        info = dfs(self, info)

        return self.add_src(src, info, filter_none=True, **kwargs)

    # Internal methods used to compute some keys from a live devlib Target

    @classmethod
    def _nrg_model_from_target(cls, target):
        logger = cls.get_logger()
        logger.info('Attempting to read energy model from target')
        try:
            return EnergyModel.from_target(target)
        except (TargetStableError, RuntimeError, ValueError) as err:
            logger.error("Couldn't read target energy model: {}".format(err))
            return None

    @classmethod
    def _read_kallsyms(cls, target):
        """
        Read and parse the content of ``/proc/kallsyms``.
        """

        def parse_line(line):
            splitted = re.split(r'\W+', line)
            addr = int(splitted[0], base=16)
            symtype = splitted[1]
            func = splitted[2]
            return addr, func

        logger = cls.get_logger()
        logger.info('Attempting to read kallsyms from target')

        try:
            with target.revertable_write_value('/proc/sys/kernel/kptr_restrict', '0'):
                kallsyms = target.read_value('/proc/kallsyms')
        except TargetStableError as e:
            logger.error("Couldn't read /proc/kallsyms: {}".format(e))
            return None

        symbols = dict(map(parse_line, kallsyms.splitlines()))
        if symbols.keys() == {0}:
            logger.error("kallsyms only contains null pointers")
            return None

        return symbols

 # vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab
