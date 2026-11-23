# Fremdsoftware

Der eigene Code von Brennweiten steht unter der [MIT-Lizenz](LICENSE). Das fertige App-Paket (DMG und ZIP) enthält zusätzlich die folgenden Komponenten. Sie bleiben unter ihren eigenen Lizenzen. Die Lizenztexte liegen in [`THIRD_PARTY_LICENSES/`](THIRD_PARTY_LICENSES) und im App-Paket unter `Contents/Resources/runtime/LIZENZEN.txt`.

| Komponente | Version | Lizenz | Lizenztext |
|---|---|---|---|
| [ExifTool](https://exiftool.org) von Phil Harvey | 13.55 | Wahlweise Perl Artistic License oder GNU GPL | `ExifTool-Perl-Artistic-License.txt`, `ExifTool-GPL.txt` |
| [Python](https://www.python.org) | 3.12.16 | PSF License | `Python-LICENSE.txt` |
| [python-build-standalone](https://github.com/astral-sh/python-build-standalone) | 20261110 | Build der oben genannten Python-Version | `Python-LICENSE.txt` |
| [OpenSSL](https://www.openssl.org) | 3.5.9 | Apache License 2.0 | `OpenSSL-LICENSE.txt` |
| [SQLite](https://sqlite.org) | 3.53.1 | Public Domain | entfällt |
| [Expat](https://libexpat.github.io) | 2.10.0 | MIT | `CPython-bundled-components.rst` |
| [libffi](https://sourceware.org/libffi/) | in Python enthalten | MIT | `CPython-bundled-components.rst` |
| [libmpdec](https://www.bytereef.org/mpdecimal/) | 4.0.0 | BSD 2-Clause | `CPython-bundled-components.rst` |
| [bzip2](https://sourceware.org/bzip2/) | in Python enthalten | BSD-artige bzip2-Lizenz | `bzip2-LICENSE.txt` |
| [XZ Utils / liblzma](https://tukaani.org/xz/) | in Python enthalten | BSD Zero Clause (0BSD) | `xz-liblzma-0BSD.txt` |
| Weitere in CPython enthaltene Komponenten | 3.12.16 | Siehe Lizenztext | `CPython-bundled-components.rst` |

ExifTool liegt im App-Paket als unveränderter Perl-Quelltext vor, nur die Dokumentationsdateien (`.pod`) fehlen. Der vollständige Quelltext ist unter <https://exiftool.org> erhältlich.

Das Build-Skript entfernt aus der Python-Laufzeit nicht benötigte Teile wie Tcl/Tk, Tests und pip. Perl, zlib, libedit und ncurses werden vom Betriebssystem bereitgestellt und nicht mitgeliefert.
