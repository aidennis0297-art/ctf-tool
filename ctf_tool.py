#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTF & Escape Room Offline Companion CLI Tool
Zero-Dependency Python 3 Utility (Standard Library Only)
"""

import sys
import os
import argparse
import base64
import urllib.parse
import re
import http.server
import socketserver
import webbrowser

SIGNATURES = [
    (b'\x89PNG\r\n\x1a\n', 'PNG', 'PNG Image'),
    (b'\xff\xd8\xff', 'JPG', 'JPEG Image'),
    (b'GIF87a', 'GIF', 'GIF87a Image'),
    (b'GIF89a', 'GIF', 'GIF89a Image'),
    (b'BM', 'BMP', 'Bitmap Image'),
    (b'PK\x03\x04', 'ZIP', 'ZIP Archive / Office Doc'),
    (b'7z\xbc\xaf\x27\x1c', '7Z', '7-Zip Archive'),
    (b'Rar!\x1a\x07', 'RAR', 'RAR Archive'),
    (b'%PDF', 'PDF', 'PDF Document'),
    (b'MZ', 'EXE', 'Windows Executable (PE/DLL)'),
    (b'\x7fELF', 'ELF', 'Linux Executable (ELF)'),
    (b'\xd4\xc3\xb2\xa1', 'PCAP', 'Wireshark PCAP (Little Endian)'),
    (b'\xa1\xb2\xc3\xd4', 'PCAP', 'Wireshark PCAP (Big Endian)'),
    (b'\x0a\r\r\x0a', 'PCAPNG', 'Wireshark PCAPNG'),
    (b'RIFF', 'WAV', 'RIFF/WAV Audio'),
    (b'ID3', 'MP3', 'MP3 Audio (ID3)'),
    (b'SQLite format 3\x00', 'SQLITE', 'SQLite Database 3')
]

ENGLISH_FREQ = {
    'e': 12.7, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0, 'n': 6.7, 's': 6.3,
    'h': 6.1, 'r': 6.0, 'd': 4.3, 'l': 4.0, 'c': 2.8, 'u': 2.8, 'm': 2.4,
    'w': 2.4, 'f': 2.2, 'g': 2.0, 'y': 2.0, 'p': 1.9, 'b': 1.5, 'v': 1.0,
    'k': 0.8, 'j': 0.15, 'x': 0.15, 'q': 0.10, 'z': 0.07, ' ': 15.0
}

def cmd_magic(args):
    """Inspect file header and check for magic bytes & extension spoofing"""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"[-] 파일이 존재하지 않습니다: {filepath}")
        return

    with open(filepath, 'rb') as f:
        header = f.read(64)

    file_size = os.path.getsize(filepath)
    ext = os.path.splitext(filepath)[1].lstrip('.').upper()

    print(f"\n[*] 파일 분석: {os.path.basename(filepath)}")
    print(f"[*] 파일 크기: {file_size:,} 바이트 ({file_size/1024:.1f} KB)")
    print(f"[*] 헤더 16바이트 (Hex): {' '.join(f'{b:02X}' for b in header[:16])}")
    print(f"[*] 헤더 16바이트 (ASCII): {''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:16])}")

    matched = None
    for sig, sig_ext, desc in SIGNATURES:
        if header.startswith(sig):
            matched = (sig_ext, desc)
            break

    print("\n--- [결과 분석] ---")
    if matched:
        sig_ext, desc = matched
        print(f"[+] 실제 파일 포맷: {desc} ({sig_ext})")
        if ext == sig_ext or (sig_ext == 'JPG' and ext in ['JPG', 'JPEG']):
            print("[+] 정상: 확장자와 파일 헤더 시그니처가 일치합니다.")
        else:
            print(f"[!] ⚠️ 경고: 확장자 위장 감지! 파일 확장자는 .{ext}이지만 실제 파일은 {sig_ext} 입니다!")
    else:
        print("[-] 알려진 바이너리 시그니처가 없거나 일반 텍스트 파일입니다.")

def cmd_strings(args):
    """Extract printable strings and search for flag patterns"""
    filepath = args.file
    min_len = args.min
    grep = args.grep.lower() if args.grep else None

    if not os.path.isfile(filepath):
        print(f"[-] 파일이 존재하지 않습니다: {filepath}")
        return

    with open(filepath, 'rb') as f:
        data = f.read()

    pattern = bytes(f'[ -~]{{{min_len},}}', 'ascii')
    matches = [m.group(0).decode('latin-1', errors='ignore') for m in re.finditer(pattern, data)]

    print(f"[*] 총 {len(matches)}개의 문자열(길이 {min_len} 이상)을 추출했습니다.")
    if grep:
        print(f"[*] 필터 검색어: '{grep}'")

    shown = 0
    for s in matches:
        if grep and grep not in s.lower():
            continue
        # Highlight flag
        is_flag = bool(re.search(r'flag\{|ctf\{', s, re.IGNORECASE))
        prefix = "🎉 [FLAG] " if is_flag else "    "
        print(f"{prefix}{s}")
        shown += 1
        if shown >= 100 and not grep:
            print("... (상위 100개만 표시됨. 특정 키워드는 -g flag 로 검색하세요) ...")
            break

def cmd_xor(args):
    """Single-byte XOR brute force or decrypt with key"""
    target = args.target
    if os.path.isfile(target):
        with open(target, 'rb') as f:
            data = f.read()
    else:
        # Check if hex string
        clean_hex = re.sub(r'[^0-9a-fA-F]', '', target)
        if len(clean_hex) % 2 == 0 and len(clean_hex) >= 2:
            try:
                data = bytes.fromhex(clean_hex)
            except ValueError:
                data = target.encode('utf-8')
        else:
            data = target.encode('utf-8')

    if args.key is not None:
        key = int(args.key, 0)
        decrypted = bytes([b ^ key for b in data])
        print(f"[*] Key 0x{key:02X} Decrypted:")
        print(decrypted.decode('latin-1', errors='ignore'))
        return

    # Brute force all 256 keys
    results = []
    for key in range(256):
        decrypted = bytes([b ^ key for b in data])
        score = 0
        text_str = decrypted.decode('latin-1', errors='ignore')
        for ch in text_str.lower():
            if ch in ENGLISH_FREQ:
                score += ENGLISH_FREQ[ch]
            elif ord(ch) < 32 or ord(ch) > 126:
                if ch not in '\r\n\t':
                    score -= 15

        if 'flag' in text_str.lower() or 'ctf' in text_str.lower():
            score += 150

        results.append((score, key, text_str[:120]))

    results.sort(key=lambda x: x[0], reverse=True)
    print("\n--- [단일 바이트 XOR 256개 키 상위 추천 결과] ---")
    for score, key, sample in results[:8]:
        ascii_char = chr(key) if 32 <= key <= 126 else ' '
        print(f"Key: 0x{key:02X} ('{ascii_char}') [점수: {score:.1f}] ➔ {sample}")

def cmd_carve(args):
    """Scan and carve embedded files (ZIP, PNG, JPEG, PDF)"""
    filepath = args.file
    out_dir = args.out or os.path.splitext(filepath)[0] + "_carved"

    if not os.path.isfile(filepath):
        print(f"[-] 파일이 존재하지 않습니다: {filepath}")
        return

    with open(filepath, 'rb') as f:
        data = f.read()

    os.makedirs(out_dir, exist_ok=True)
    print(f"[*] 파일 카빙 스캔 시작: {filepath} ({len(data):,} 바이트)")

    carved_count = 0
    # Search for ZIP
    zip_matches = [m.start() for m in re.finditer(b'PK\x03\x04', data)]
    for idx, offset in enumerate(zip_matches):
        if offset == 0: continue # Primary header
        out_path = os.path.join(out_dir, f"carved_{carved_count:02d}_offset_0x{offset:X}.zip")
        with open(out_path, 'wb') as out_f:
            out_f.write(data[offset:])
        print(f"[+] 발견 및 추출: ZIP 압축파일 (오프셋 0x{offset:X}) ➔ {out_path}")
        carved_count += 1

    # Search for PNG
    png_matches = [m.start() for m in re.finditer(b'\x89PNG\r\n\x1a\n', data)]
    for idx, offset in enumerate(png_matches):
        if offset == 0: continue
        out_path = os.path.join(out_dir, f"carved_{carved_count:02d}_offset_0x{offset:X}.png")
        with open(out_path, 'wb') as out_f:
            out_f.write(data[offset:])
        print(f"[+] 발견 및 추출: PNG 이미지 (오프셋 0x{offset:X}) ➔ {out_path}")
        carved_count += 1

    # Search for JPEG
    jpg_matches = [m.start() for m in re.finditer(b'\xff\xd8\xff', data)]
    for idx, offset in enumerate(jpg_matches):
        if offset == 0: continue
        out_path = os.path.join(out_dir, f"carved_{carved_count:02d}_offset_0x{offset:X}.jpg")
        with open(out_path, 'wb') as out_f:
            out_f.write(data[offset:])
        print(f"[+] 발견 및 추출: JPEG 이미지 (오프셋 0x{offset:X}) ➔ {out_path}")
        carved_count += 1

    if carved_count == 0:
        print("[-] 파일 내부에 중첩된 다른 파일 시그니처가 발견되지 않았습니다.")
    else:
        print(f"[+] 카빙 완료! 총 {carved_count}개의 파일이 '{out_dir}' 폴더에 저장되었습니다.")

def cmd_decode(args):
    """Auto decode Base64, Hex, URL, ROT13, Caesar shifts"""
    s = args.text.strip()
    print(f"\n[*] 입력 문자열: {s}\n")

    # 1. Base64
    try:
        b64_dec = base64.b64decode(s).decode('utf-8', errors='replace')
        print(f"[Base64 디코딩]   ➔ {b64_dec}")
    except Exception:
        pass

    # 2. Hex
    clean_hex = re.sub(r'[^0-9a-fA-F]', '', s)
    if len(clean_hex) % 2 == 0 and len(clean_hex) >= 2:
        try:
            hex_dec = bytes.fromhex(clean_hex).decode('utf-8', errors='replace')
            print(f"[16진수 디코딩]    ➔ {hex_dec}")
        except Exception:
            pass

    # 3. URL
    try:
        url_dec = urllib.parse.unquote(s)
        if url_dec != s:
            print(f"[URL 디코딩]      ➔ {url_dec}")
    except Exception:
        pass

    # 4. ROT13
    rot13_dec = s.translate(str.maketrans(
        "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz",
        "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm"
    ))
    print(f"[ROT13 변환]      ➔ {rot13_dec}")

    # 5. Caesar shifts check
    print("\n--- [시저(Caesar) 25개 시프트] ---")
    for shift in range(1, 26):
        shifted = []
        for ch in s:
            if 'A' <= ch <= 'Z':
                shifted.append(chr((ord(ch) - 65 + shift) % 26 + 65))
            elif 'a' <= ch <= 'z':
                shifted.append(chr((ord(ch) - 97 + shift) % 26 + 97))
            else:
                shifted.append(ch)
        res = ''.join(shifted)
        if any(kw in res.upper() for kw in ['FLAG', 'CTF', 'THE', 'KEY', 'PASS', 'SECRET']):
            print(f"Shift +{shift:02d} [추천!]: {res}")
        elif shift in [1, 3, 13]:
            print(f"Shift +{shift:02d}:         {res}")

def cmd_serve(args):
    """Start offline local HTTP web server and open browser"""
    port = args.port
    directory = os.path.dirname(os.path.abspath(__file__))
    os.chdir(directory)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print("=" * 60)
        print("🚀 [CTF & 방탈출 올인원 수사 워크벤치 로컬 서버 가동]")
        print(f"[*] 웹 브라우저 주소: {url}")
        print(f"[*] 같은 Wi-Fi/핫스팟 팀원 접속 주소: http://[내_IP]:{port}")
        print("[*] 종료하려면 터미널에서 Ctrl + C 를 누르세요.")
        print("=" * 60)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버가 종료되었습니다.")

def main():
    parser = argparse.ArgumentParser(
        description="CTF & 방탈출 오프라인 컴패니언 CLI 툴 (Zero-Dependency)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="실행할 하위 명령어")

    # magic
    p_magic = subparsers.add_parser("magic", help="파일 헤더 매직 바이트 검사 및 확장자 위장 감지")
    p_magic.add_argument("file", help="분석할 대상 파일 경로")
    p_magic.set_defaults(func=cmd_magic)

    # strings
    p_strings = subparsers.add_parser("strings", help="바이너리 내 출력 가능 문자열 및 플래그 추출")
    p_strings.add_argument("file", help="분석할 대상 파일 경로")
    p_strings.add_argument("-n", "--min", type=int, default=4, help="최소 문자열 길이 (기본: 4)")
    p_strings.add_argument("-g", "--grep", type=str, help="검색할 특정 키워드 (예: flag, key)")
    p_strings.set_defaults(func=cmd_strings)

    # xor
    p_xor = subparsers.add_parser("xor", help="단일 바이트 XOR 전수조사 및 복호화")
    p_xor.add_argument("target", help="암호화된 문자열, 16진수 바이트열, 또는 파일 경로")
    p_xor.add_argument("-k", "--key", help="특정 XOR 키 (예: 0x42 또는 66)")
    p_xor.set_defaults(func=cmd_xor)

    # carve
    p_carve = subparsers.add_parser("carve", help="파일 속 중첩된 숨은 파일(ZIP, PNG, JPG) 추출")
    p_carve.add_argument("file", help="분석할 대상 파일 경로")
    p_carve.add_argument("-o", "--out", help="추출된 파일을 저장할 폴더")
    p_carve.set_defaults(func=cmd_carve)

    # decode
    p_decode = subparsers.add_parser("decode", help="Base64, Hex, URL, ROT13, 시저 일괄 자동 디코딩")
    p_decode.add_argument("text", help="디코딩할 문자열")
    p_decode.set_defaults(func=cmd_decode)

    # serve
    p_serve = subparsers.add_parser("serve", help="로컬 웹 서버 구동 및 워크벤치 브라우저 열기")
    p_serve.add_argument("-p", "--port", type=int, default=8000, help="포트 번호 (기본: 8000)")
    p_serve.set_defaults(func=cmd_serve)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
