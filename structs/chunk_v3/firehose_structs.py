from base_chunk import Header


class Metadata(Header):
    """https://github.com/libyal/dtformats/blob/main/documentation/Apple%20Unified%20Logging%20and%20Activity%20Tracing%20formats.asciidoc#27-firehose-chunk"""

    @staticmethod
    def _fmt() -> str:
        return super(Metadata, Metadata)._fmt() + "B4H2BQ"

    @property
    def collapsed(self):
        """'Collapsed' indicates if the empty bytes in between have been removed to shrink the block.
         Size of private data can be calculated by subtracting virtual offset from 4096."""
        return self._values[3]

    @property
    def public_data_size(self):
        return self._values[5]

    @property
    def private_data_offset(self):
        return self._values[6]

    @property
    def stream_type(self):
        return self._values[8]

    @property
    def time_events(self):
        return self._values[10]
