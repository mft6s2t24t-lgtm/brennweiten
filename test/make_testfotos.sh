#!/bin/bash
# Erzeugt einen Testordner mit bekannten EXIF-Werten
cd "$(dirname "$0")" || exit 1
T=testfotos; J=t/clean.jpg; R=t/clean.tif
rm -rf "$T"; mkdir -p "$T/2023" "$T/2024" "$T/Export DxO" "$T/Handy"
mk(){ src=$1; dst=$2; shift 2; cp "$src" "$dst"; exiftool -q -q -overwrite_original "$@" "$dst"; }
NZ8=(-Make="NIKON CORPORATION" -Model="NIKON Z 8" -SerialNumber=3001234 -Software="Ver.02.00")
NZ6=(-Make="NIKON CORPORATION" -Model="NIKON Z 6_3" -SerialNumber=6005555 -Software="Ver.01.10")
R7=(-Make="Canon" -Model="Canon EOS R7" -SerialNumber=012345678901 -Software="Firmware Version 1.4.0")
Z=(-LensModel="NIKKOR Z 24-120mm f/4 S" -LensInfo="24 120 4 4" -MaxApertureValue=4)
mk $R $T/2024/DSC_0001.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=24 -FocalLengthIn35mmFormat=24 -FNumber=4 -ISO=6400 -ExposureTime=0.02 -DateTimeOriginal="2024:03:01 20:00:00" -SubSecTimeOriginal=12
mk $J $T/2024/DSC_0001.JPG "${NZ8[@]}" "${Z[@]}" -FocalLength=24 -FocalLengthIn35mmFormat=24 -FNumber=4 -ISO=6400 -ExposureTime=0.02 -DateTimeOriginal="2024:03:01 20:00:00" -SubSecTimeOriginal=12
mk $J "$T/Export DxO/DSC_0001_DxO.jpg" -Make="NIKON CORPORATION" -Model="NIKON Z 8" "${Z[@]}" -FocalLength=24 -FocalLengthIn35mmFormat=24 -FNumber=4 -ISO=6400 -DateTimeOriginal="2024:03:01 20:00:00" -Software="DxO PhotoLab 8"
exiftool -q -q -o $T/2024/DSC_0001.NEF.xmp -XMP:Rating=4
mk $R $T/2024/DSC_0002.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=120 -FocalLengthIn35mmFormat=120 -FNumber=5.6 -ISO=400 -DateTimeOriginal="2024:03:02 10:00:00" -SubSecTimeOriginal=50 -XMP:Rating=2
mk $R $T/2024/DSC_0003.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=70 -FocalLengthIn35mmFormat=70 -FNumber=4 -ISO=100 -DateTimeOriginal="2024:03:02 10:00:01" -SubSecTimeOriginal=10
mk $R $T/2024/DSC_0004.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=50 -FocalLengthIn35mmFormat=75 -FNumber=4 -ISO=200 -DateTimeOriginal="2024:03:02 11:00:00" -SubSecTimeOriginal=20
mk $R $T/2024/DSC_0005.NEF "${NZ6[@]}" -FocalLength=85 -FocalLengthIn35mmFormat=85 -FNumber=1.8 -MaxApertureValue=1.8 -ISO=6400 -DateTimeOriginal="2024:06:01 22:00:00" -SubSecTimeOriginal=33 -XMP:Rating=5
mk $R $T/2024/DSC_0006.NEF "${NZ6[@]}" -FocalLength=85 -FocalLengthIn35mmFormat=85 -FNumber=2.8 -MaxApertureValue=1.8 -ISO=200 -DateTimeOriginal="2024:06:01 22:01:00" -SubSecTimeOriginal=44
mk $R $T/2023/IMG_0007.CR2 "${R7[@]}" -LensModel="EF-S10-18mm f/4.5-5.6 IS STM" -FocalLength=10 -FNumber=4.5 -MaxApertureValue=4.5 -ISO=3200 -DateTimeOriginal="2023:08:01 12:00:00" -SubSecTimeOriginal=00
mk $R $T/2023/IMG_0008.CR2 "${R7[@]}" -LensModel="Canon EF-S 10-18mm f/4.5-5.6 IS STM" -FocalLength=12 -FNumber=8 -ISO=100 -DateTimeOriginal="2023:08:01 12:05:00" -SubSecTimeOriginal=00
mk $R $T/2023/IMG_0009.CR2 "${R7[@]}" -LensModel="RF-S18-150mm F3.5-6.3 IS STM" -LensInfo="18 150 3.5 6.3" -FocalLength=31 -FocalLengthIn35mmFormat=31 -FNumber=5 -ISO=12800 -DateTimeOriginal="2023:12:24 18:00:00" -SubSecTimeOriginal=05
mk $R $T/2023/IMG_0010.CR2 "${R7[@]}" -LensModel="RF-S18-150mm F3.5-6.3 IS STM" -LensInfo="18 150 3.5 6.3" -FocalLength=150 -FNumber=6.3 -MaxApertureValue=6.3 -ISO=6400 -DateTimeOriginal="2023:12:24 18:10:00" -SubSecTimeOriginal=06
mk $R $T/2024/DSC_0011.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=35 -FocalLengthIn35mmFormat=35 -FNumber=8 -ISO=100 -DateTimeOriginal="2024:07:01 09:00:00"
mk $R $T/2024/DSC_0012.NEF "${NZ8[@]}" "${Z[@]}" -FocalLength=36 -FocalLengthIn35mmFormat=36 -FNumber=8 -ISO=100 -DateTimeOriginal="2024:07:01 09:00:00" -Artist="anderes Bild"
cp $T/2024/DSC_0011.NEF $T/2023/DSC_0011_backup.NEF
mk $J $T/Handy/IMG_1234.JPG -Make=Apple -Model="iPhone 15 Pro" -FocalLength=6.8 -FocalLengthIn35mmFormat=24 -FNumber=1.8 -ISO=50 -DateTimeOriginal="2024:05:05 12:00:00"
cp $J $T/Handy/scan.jpg
