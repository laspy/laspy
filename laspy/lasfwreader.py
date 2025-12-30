import logging
import os
from .waveform import WaveformPacketDescriptorRegistry, WaveformRecord
from pathlib import Path
from ._compression.selection import DecompressionSelection
from collections.abc import Iterable
from ._compression.backend import LazBackend
from typing import BinaryIO, Optional, Union
from .lasreader import LasReader


logger = logging.getLogger(__name__)

class WaveReader:
    def __init__(
        self,
        source: BinaryIO,
        bits_per_sample: int,
        number_of_samples: int,
        closefd: bool = True,
    ):
        self._source = source
        self.bits_per_sample = bits_per_sample
        self.number_of_samples = number_of_samples
        self._closefd = closefd

    @property
    def source(self) -> BinaryIO:
        return self._source

    def read_n_waveforms(self, n: int) -> bytearray:
        wave_size_bytes = (self.bits_per_sample // 8) * self.number_of_samples
        total_size = n * wave_size_bytes
        data = self._source.read(total_size)
        return bytearray(data)

    def seek(self, waveform_index: int) -> None:
        wave_size_bytes = (self.bits_per_sample // 8) * self.number_of_samples
        offset = waveform_index * wave_size_bytes
        self._source.seek(offset)

    def close(self) -> None:
        if self._closefd:
            self._source.close()


class LasFWReader(LasReader):
    def __init__(
        self,
        source: BinaryIO,
        closefd: bool = True,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
        read_evlrs: bool = True,
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
    ):
        super().__init__(
            source,
            closefd=closefd,
            laz_backend=laz_backend,
            read_evlrs=read_evlrs,
            decompression_selection=decompression_selection,
        )
        if not self.header.point_format.has_waveform_packet:
            raise ValueError("Point format does not carry waveform attributes")

        if not self.header.global_encoding.waveform_data_packets_external:
            raise ValueError(
                "This reader expects waveform data to live in an external .wdp file"
            )

        las_path = Path(source.name)
        waveform_file = las_path.with_suffix(".wdp").open("rb")
        self._waveform_descriptors_registry = (
            WaveformPacketDescriptorRegistry.from_vlrs(self.header.vlrs)
        )
        self._waveform_source = WaveReader(
            waveform_file,
            bits_per_sample=self._waveform_descriptors_registry.bits_per_sample,
            number_of_samples=self._waveform_descriptors_registry.number_of_samples,
            closefd=True,
        )
        self.waves_read = 0
        self.total_waves = waveform_file.seek(0, os.SEEK_END) // (
            (self._waveform_descriptors_registry.bits_per_sample // 8)
            * self._waveform_descriptors_registry.number_of_samples
        )
        waveform_file.seek(0, os.SEEK_SET)

    def read_waveforms(self, n: int) -> WaveformRecord:
        waves_left = self.total_waves - self.waves_read
        if waves_left <= 0:
            return WaveformRecord.empty(
                self._waveform_descriptors_registry.dtype(),
                self._waveform_descriptors_registry.number_of_samples,
                self._waveform_descriptors_registry.temporal_sample_spacing,
            )
        
        if n < 0:
            n = waves_left
        else:
            n = min(n, waves_left)
        record = WaveformRecord.from_buffer(
            self._waveform_source.read_n_waveforms(n),
            self._waveform_descriptors_registry.dtype(),
            self._waveform_descriptors_registry.number_of_samples,
            self._waveform_descriptors_registry.temporal_sample_spacing,
        )
        if len(record) < n:
            logger.warning(f"Could only read {len(record)} waveforms, requested {n}")
        self.waves_read += len(record)
        return record