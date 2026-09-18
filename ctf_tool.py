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

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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
        # Highlight flag (SHA, FLAG, CTF)
        is_flag = bool(re.search(r'sha\{|flag\{|ctf\{', s, re.IGNORECASE))
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

def cmd_cribdrag(args):
    """Multi-byte XOR crib dragging analyzer"""
    c1_hex = args.c1.replace("0x", "").replace(" ", "")
    c2_hex = args.c2.replace("0x", "").replace(" ", "")
    crib = args.crib.encode('utf-8')

    b1 = bytes.fromhex(c1_hex)
    b2 = bytes.fromhex(c2_hex)
    min_len = min(len(b1), len(b2))

    xor_bytes = bytes([b1[i] ^ b2[i] for i in range(min_len)])
    print(f"\n[*] C1 XOR C2 ({min_len} 바이트): {xor_bytes.hex()}")
    print(f"[*] 추정 키워드(Crib): {args.crib} ({len(crib)}B)\n")

    results = []
    for offset in range(min_len - len(crib) + 1):
        cand = bytes([xor_bytes[offset + j] ^ crib[j] for j in range(len(crib))])
        printable = sum(1 for b in cand if 32 <= b <= 126 or b in (9, 10))
        score = int((printable / len(crib)) * 100)
        cand_str = cand.decode('latin-1', errors='replace')
        results.append((score, offset, cand_str))

    results.sort(key=lambda x: x[0], reverse=True)
    print(f"{'오프셋':<8} {'가독성':<8} {'대응 평문 조각 (P2)'}")
    print("-" * 50)
    for score, offset, cand_str in results[:20]:
        star = "[*]" if score >= 80 else ("   " if score < 50 else " - ")
        print(f"#{offset:<7} {score}% {star}  {cand_str}")

def cmd_rsa(args):
    """RSA algebraic attack calculator (small-e, common-mod, fermat)"""
    mode = args.mode
    if mode == "smalle":
        c = int(args.c, 0)
        e = int(args.e, 0) if args.e else 3
        low = 1
        high = c
        ans = 0
        while low <= high:
            mid = (low + high) // 2
            if mid ** e == c:
                ans = mid
                break
            elif mid ** e < c:
                ans = mid
                low = mid + 1
            else:
                high = mid - 1
        print(f"[*] 평문 m (int): {ans}")
        print(f"[*] 평문 m (hex): {hex(ans)}")
        try:
            m_bytes = ans.to_bytes((ans.bit_length() + 7) // 8, 'big')
            print(f"[+] 평문 m (ASCII/UTF-8): {m_bytes.decode('utf-8')}")
        except Exception:
            pass

    elif mode == "commonmod":
        N = int(args.n, 0)
        e1 = int(args.e1, 0)
        c1 = int(args.c1, 0)
        e2 = int(args.e2, 0)
        c2 = int(args.c2, 0)
        def egcd(a, b):
            if b == 0: return (a, 1, 0)
            g, x, y = egcd(b, a % b)
            return (g, y, x - (a // b) * y)
        g, r, s = egcd(e1, e2)
        if g != 1:
            print(f"[-] gcd(e1, e2) = {g} != 1")
            return
        if r < 0:
            c1 = pow(c1, -1, N)
            r = -r
        if s < 0:
            c2 = pow(c2, -1, N)
            s = -s
        m = (pow(c1, r, N) * pow(c2, s, N)) % N
        print(f"[+] 공통 모듈러스 복호화 성공:")
        print(f"[*] 평문 m (int): {m}")
        print(f"[*] 평문 m (hex): {hex(m)}")
        try:
            m_bytes = m.to_bytes((m.bit_length() + 7) // 8, 'big')
            print(f"[+] 평문 m (ASCII/UTF-8): {m_bytes.decode('utf-8')}")
        except Exception:
            pass

    elif mode == "fermat":
        import math
        N = int(args.n, 0)
        a = math.isqrt(N)
        if a * a < N: a += 1
        b2 = a * a - N
        b = math.isqrt(b2)
        steps = 0
        while b * b != b2 and steps < 500000:
            a += 1
            b2 = a * a - N
            b = math.isqrt(b2)
            steps += 1
        if b * b == b2:
            p = a + b
            q = a - b
            print(f"[+] 페르마 소인수분해 성공! ({steps} 스텝)")
            print(f"[*] p: {p}")
            print(f"[*] q: {q}")
            print(f"[*] phi: {(p-1)*(q-1)}")
        else:
            print("[-] 페르마 한도 초과: p와 q의 차이가 큽니다.")

def cmd_bitflip(args):
    """AES-CBC IV bit-flipping calculator"""
    iv = bytes.fromhex(args.iv.replace("0x", "").replace(" ", ""))
    p_orig = args.orig.encode('utf-8')
    p_target = args.target.encode('utf-8')
    new_iv = bytearray(iv)
    for i in range(min(16, max(len(p_orig), len(p_target)))):
        o = p_orig[i] if i < len(p_orig) else 0
        t = p_target[i] if i < len(p_target) else 0
        new_iv[i] = iv[i] ^ o ^ t
    print(f"\n[+] 원본 IV: {iv.hex()}")
    print(f"[+] 변조된 IV': {new_iv.hex()}")
    print(f"[*] 치환: '{args.orig}' -> '{args.target}'\n")

def cmd_creds(args):
    """Display team credentials and operational links"""
    print("\n" + "="*65)
    print("🍜 [서울시립대 방탈출 CTF] 라면물조절장인 팀 정보 & 계정 치트시트")
    print("="*65)
    print("팀명: 라면물조절장인")
    print("대회: 2026.09.19 (토) 10:00 ~ 18:30 (현장 접수 마감: 10:00)")
    print("장소: 서울시립대학교 21세기관 국제회의장 (& 교내 5개 건물)")
    print("Wi-Fi: Guest@UOS (타대생 전용 무선 네트워크)")
    print("제출처: roomescapectf2026@gmail.com (17:30 마감 엄수)")
    print("공식 디스코드: https://discord.gg/BENmZ3sQ9")
    print("-" * 65)
    print("선수 계정 정보 (초기 비밀번호):")
    print("  1) 전성호: dennis0297@naver.com")
    print("     임시PW: e6a11949beadc7d457144e6f0d0937f5be952c9a643afd2bf80a3b2d56b099f0")
    print("  2) 이도경: ldk02045@naver.com")
    print("     임시PW: df37dc82e3eaf9c2422fc7eec6a077ba9500d196ca4ca924985de52181c76431")
    print("  3) 조성현: josung0812@naver.com")
    print("     임시PW: fba88c0675cedb477b40bb8b6746c852529b17d44e7e59154c553e95b817895b")
    print("="*65 + "\n")

def cmd_shacheck(args):
    """Validate flag against official SHA CTF specifications"""
    flag = args.flag.strip()
    print(f"\n🚩 [플래그 규격 검증: {flag}]")
    pattern = r'^SHA\{([A-Za-z0-9_가-힣]+)\}$'
    match = re.match(pattern, flag)
    if match:
        body = match.group(1)
        print("[+] ✅ 정규식 통과! 공식 SHA CTF 플래그 규격에 부합합니다.")
        print(f"[*] 플래그 본문: '{body}'")
        has_kor = bool(re.search(r'[가-힣]', body))
        has_num = bool(re.search(r'[0-9]', body))
        has_alpha = bool(re.search(r'[A-Za-z]', body))
        has_underscore = '_' in body
        print(f"[*] 구성 요소: 한글({has_kor}), 영문({has_alpha}), 숫자({has_num}), 언더바({has_underscore})")
    else:
        print("[-] ❌ 플래그 규격 불일치!")
        if not flag.startswith("SHA{"):
            print("  - 'SHA{' 접두사가 누락되었거나 대소문자가 일치하지 않습니다.")
        if not flag.endswith("}"):
            print("  - 닫는 중괄호 '}'가 누락되었습니다.")
        if re.search(r'[^A-Za-z0-9_가-힣]', flag[4:-1] if len(flag) > 5 else ''):
            print("  - 허용되지 않은 특수문자 또는 공백/줄바꿈이 포함되어 있습니다. (공식 허용: 알파벳, 한글, 숫자, 밑줄)")
    print()

def cmd_lock(args):
    """Analyze lock combinations, 180-deg rotation (6 vs 9), directional lock, and confusion mapping"""
    val = args.code.strip()
    map180 = {
        '0': '0', '1': '1', '6': '9', '8': '8', '9': '6',
        '2': '2', '5': '5', 'b': 'q', 'd': 'p', 'p': 'd', 'q': 'b',
        'n': 'u', 'u': 'n', 'w': 'm', 'm': 'w'
    }
    inv = []
    strict = True
    for ch in reversed(val.lower()):
        if ch in map180:
            inv.append(map180[ch])
        else:
            inv.append(ch + '?')
            strict = False
    inv_str = ''.join(inv)

    print(f"\n🔐 [공식 자물쇠 도우미 - 코드 분석: {val}]")
    print(f"[*] 원본 입력값: {val}")
    print(f"[*] 180° 상하 반전 (거꾸로 보았을 때): {inv_str} {'(완전 대칭)' if strict else '(비대칭 문자 포함)'}")

    # Directional lock check
    dir_map = {'상': 'U', '하': 'D', '좌': 'L', '우': 'R', '위': 'U', '아래': 'D', '왼': 'L', '오': 'R', 'U': 'U', 'D': 'D', 'L': 'L', 'R': 'R'}
    dir_seq = [dir_map[c] for c in val.upper() if c in dir_map or c in dir_map.values()]
    if dir_seq:
        seq_str = ''.join(dir_seq)
        seq_num = ''.join({'U':'1','D':'2','L':'3','R':'4'}[d] for d in dir_seq)
        seq_pad = ''.join({'U':'8','D':'2','L':'4','R':'6'}[d] for d in dir_seq)
        print(f"\n🧭 [방향 자물쇠 변환 감지]")
        print(f"[*] 방향 시퀀스: {seq_str}")
        print(f"[*] 순차 번호 (1234): {seq_num}")
        print(f"[*] 키패드 번호 (8246): {seq_pad}")

    print("\n--- [공식 가이드라인 및 주의사항] ---")
    print("1. 확인 위치: 빨간 점이나 지시선에 정확히 수평 정렬 후 가볍게 당겨야 열립니다.")
    print("2. 6 vs 9 유의: 거꾸로 돌렸을 때 6이 9로, 9가 6으로 보일 수 있습니다.")
    print("3. 혼동 쉬운 문자: O(오)↔0(영), I/l(아이/엘)↔1(일), S(에스)↔5(오), B(비)↔8(팔), Z(제트)↔2(이)")
    print("4. 방향 자물쇠: 시작 전 섀클을 2회 아래로 꾹 눌러 '딸깍' 리셋 필수!\n")

def cmd_checkreport(args):
    """Validate Article 8 report compliance for SHA x Doorlock competition"""
    import json
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"[-] 파일이 존재하지 않습니다: {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"\n📑 [공식 제8조 수사보고서 사전 검증: {os.path.basename(filepath)}]")
    warnings = []
    passes = []

    if filepath.endswith('.json'):
        try:
            data = json.loads(content)
            clues = data.get('clues', data if isinstance(data, list) else [])
            scenes = data.get('crimeScenes', [])
            print(f"[*] 등록된 단서 수: {len(clues)}개, 수사 현장: {len(scenes)}개")

            missing_src = [c for c in clues if not c.get('room') or not c.get('location')]
            if missing_src:
                warnings.append(f"출처(방/위치) 누락 단서 {len(missing_src)}건: {', '.join(c.get('title', '무제') for c in missing_src)}")
            else:
                passes.append("모든 단서의 출처(방 이름, 구체적 위치) 기재 완료")

            missing_inf = [c for c in clues if not c.get('inference')]
            if missing_inf:
                warnings.append(f"추론 연계 내용 누락 단서 {len(missing_inf)}건: {', '.join(c.get('title', '무제') for c in missing_inf)}")
            else:
                passes.append("모든 단서의 추론 연계 증거 기재 완료")

            re_entries = [s for s in scenes if s.get('entries', 1) > 1]
            if re_entries:
                warnings.append(f"1회 초과 입장(재입장) 발생 현장: {', '.join(s.get('name', '') for s in re_entries)} -> 퍼펙트 실격")
            else:
                passes.append("5대 현장 모두 1회 입장 준수")
        except Exception as e:
            print(f"[-] JSON 파싱 오류: {e}")
            return
    else:
        if '추론 내용' in content:
            passes.append("추론 내용(제8조 1항) 섹션 존재 확인")
        else:
            warnings.append("추론 내용 섹션이 누락되었습니다.")

        if '출처' in content:
            passes.append("출처(제8조 3항) 명시 확인")
        else:
            warnings.append("출처(방 이름 및 발견 위치) 명시가 부족합니다.")

    print("\n--- [검증 결과 요약] ---")
    for p in passes:
        print(f"  [+] {p}")
    for w in warnings:
        print(f"  [!] ⚠️ 감점 주의: {w}")

    if not warnings:
        print("\n✅ 제8조 감점 위험 요소 0건! 3,000점 만점 제출 준비 완료!\n")
    else:
        print(f"\n⚠️ 총 {len(warnings)}건의 보완 사항이 있습니다. 제출 전 반드시 수정하세요!\n")

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

    # cribdrag
    p_crib = subparsers.add_parser("cribdrag", help="다중 XOR 키 재사용 크립 드래깅(Crib Dragging)")
    p_crib.add_argument("c1", help="첫 번째 암호문 (Hex)")
    p_crib.add_argument("c2", help="두 번째 암호문 (Hex)")
    p_crib.add_argument("-c", "--crib", required=True, help="추정 키워드 (예: 'the ', 'FLAG{')")
    p_crib.set_defaults(func=cmd_cribdrag)

    # rsa
    p_rsa = subparsers.add_parser("rsa", help="RSA 대수 공격 (smalle, commonmod, fermat)")
    p_rsa.add_argument("mode", choices=["smalle", "commonmod", "fermat"], help="공격 모드")
    p_rsa.add_argument("-c", help="암호문 c")
    p_rsa.add_argument("-e", help="공개 지수 e (기본 3)")
    p_rsa.add_argument("-n", help="모듈러스 N")
    p_rsa.add_argument("-e1", help="지수 1")
    p_rsa.add_argument("-c1", help="암호문 1")
    p_rsa.add_argument("-e2", help="지수 2")
    p_rsa.add_argument("-c2", help="암호문 2")
    p_rsa.set_defaults(func=cmd_rsa)

    # bitflip
    p_flip = subparsers.add_parser("bitflip", help="AES-CBC IV 비트 플리핑 계산")
    p_flip.add_argument("iv", help="원본 IV (Hex)")
    p_flip.add_argument("orig", help="원본 첫 블록 평문")
    p_flip.add_argument("target", help="변조 목표 평문")
    p_flip.set_defaults(func=cmd_bitflip)

    # lock
    p_lock = subparsers.add_parser("lock", help="공식 자물쇠 180도 반전(6 vs 9) 및 혼동 문자 분석")
    p_lock.add_argument("code", help="분석할 자물쇠 숫자/문자 코드")
    p_lock.set_defaults(func=cmd_lock)

    # checkreport
    p_rep = subparsers.add_parser("checkreport", help="수사보고서 제8조 규격 및 감점 위험 전수 검증")
    p_rep.add_argument("file", help="검증할 수사보고서(.md) 또는 수사보드 백업(.json)")
    p_rep.set_defaults(func=cmd_checkreport)

    # carve
    p_carve = subparsers.add_parser("carve", help="파일 속 중첩된 숨은 파일(ZIP, PNG, JPG) 추출")
    p_carve.add_argument("file", help="분석할 대상 파일 경로")
    p_carve.add_argument("-o", "--out", help="추출된 파일을 저장할 폴더")
    p_carve.set_defaults(func=cmd_carve)

    # decode
    p_decode = subparsers.add_parser("decode", help="Base64, Hex, URL, ROT13, 시저 일괄 자동 디코딩")
    p_decode.add_argument("text", help="디코딩할 문자열")
    p_decode.set_defaults(func=cmd_decode)

    # creds
    p_creds = subparsers.add_parser("creds", help="라면물조절장인 팀 정보 및 선수 계정 치트시트 출력")
    p_creds.set_defaults(func=cmd_creds)

    # sha-check
    p_shacheck = subparsers.add_parser("sha-check", help="공식 SHA CTF 플래그 규격(SHA{...}) 및 문자셋 검증")
    p_shacheck.add_argument("flag", help="검증할 플래그 문자열")
    p_shacheck.set_defaults(func=cmd_shacheck)

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

