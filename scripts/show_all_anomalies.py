#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Выводит все аномалии с указанием файла и номера строки
"""

import re
from pathlib import Path
from collections import defaultdict

# Кириллица, цифры, основные знаки препинания, пробельные символы
RUSSIAN_CHARS = set('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя0123456789')
PUNCTUATION = set('.,;:!?-"()[]{}«»—–…')
WHITESPACE = set(' \n\r\t')
ALLOWED_CHARS = RUSSIAN_CHARS | PUNCTUATION | WHITESPACE

# Паттерны для названий глав
CHAPTER_PATTERNS = [
    r'^[IVXLCDM]+$',
    r'^ГЛАВА\s+[IVXLCDM\d]+',
    r'^ЧАСТЬ\s+[IVXLCDM\d]+',
    r'^[ГЧ]\s*[IVXLCDM\d]+',
    r'^\d+$',
]

def is_likely_chapter_title(line):
    """Проверяет, является ли строка названием главы"""
    stripped = line.strip()
    if not stripped:
        return False
    
    for pattern in CHAPTER_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    
    if len(stripped) < 30 and stripped.isupper() and stripped.replace(' ', '').isalpha():
        return True
    
    return False

def find_anomalies_in_file(filepath):
    """Находит все аномалии в файле"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='cp1251') as f:
                lines = f.readlines()
        except Exception as e:
            return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}
    
    anomalies = {
        'tokens': [],  # Токены (base64)
        'multiple_unusual': [],  # Множественные необычные символы
        'unusual_symbols': [],  # Отдельные необычные символы
        'latin_in_russian': []  # Латиница в русском тексте
    }
    
    token_pattern = re.compile(r'^[A-Za-z0-9+/=]{40,}$')
    
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Пропускаем пустые строки и названия глав
        if not stripped or is_likely_chapter_title(line):
            continue
        
        # Проверка на токены (base64)
        if token_pattern.match(stripped) and len(stripped) > 40:
            anomalies['tokens'].append((line_num, stripped[:100]))
            continue
        
        # Проверка на множественные необычные символы подряд
        if re.search(r'[^\w\s\u0400-\u04FF.,;:!?\-"()\[\]{}«»—–…]{3,}', line):
            anomalies['multiple_unusual'].append((line_num, stripped[:150]))
        
        # Проверка на необычные символы и латиницу
        has_russian = any(c in RUSSIAN_CHARS for c in line)
        suspicious_chars = []
        latin_chars = []
        
        for i, char in enumerate(line):
            if char not in ALLOWED_CHARS:
                if char.isalpha() and ord(char) < 128:
                    latin_chars.append((i, char))
                else:
                    suspicious_chars.append((i, char, hex(ord(char))))
        
        if has_russian:
            if latin_chars and len(latin_chars) > 5:
                anomalies['latin_in_russian'].append((line_num, stripped[:150]))
            if suspicious_chars:
                anomalies['unusual_symbols'].append((line_num, stripped[:150]))
    
    return anomalies

def main():
    script_dir = Path(__file__).parent
    txt_files = sorted(script_dir.glob('*.txt'))
    
    # Исключаем служебные файлы
    exclude_files = {'find_anomalies.py', 'create_summary.py', 'show_all_anomalies.py',
                     'anomalies_report.txt', 'summary_report.txt', 'analysis_output.txt'}
    txt_files = [f for f in txt_files if f.name not in exclude_files]
    
    print("="*80)
    print("ВСЕ АНОМАЛИИ С УКАЗАНИЕМ СТРОК")
    print("="*80)
    print()
    
    total_files_with_anomalies = 0
    
    for txt_file in txt_files:
        anomalies = find_anomalies_in_file(txt_file)
        
        if 'error' in anomalies:
            continue
        
        has_any = any(anomalies[key] for key in anomalies)
        if not has_any:
            continue
        
        total_files_with_anomalies += 1
        print(f"\n{'='*80}")
        print(f"📄 {txt_file.name}")
        print('='*80)
        
        # Токены (критичные)
        if anomalies['tokens']:
            print(f"\n🔴 ТОКЕНЫ (BASE64) - {len(anomalies['tokens'])} случаев:")
            print("-"*80)
            for line_num, token in anomalies['tokens'][:20]:  # Показываем первые 20
                print(f"  Строка {line_num:5d}: {token}...")
            if len(anomalies['tokens']) > 20:
                print(f"  ... и еще {len(anomalies['tokens']) - 20} токенов")
        
        # Множественные необычные символы
        if anomalies['multiple_unusual']:
            print(f"\n⚠️  МНОЖЕСТВЕННЫЕ НЕОБЫЧНЫЕ СИМВОЛЫ - {len(anomalies['multiple_unusual'])} случаев:")
            print("-"*80)
            for line_num, line in anomalies['multiple_unusual'][:15]:  # Показываем первые 15
                print(f"  Строка {line_num:5d}: {line}...")
            if len(anomalies['multiple_unusual']) > 15:
                print(f"  ... и еще {len(anomalies['multiple_unusual']) - 15} случаев")
        
        # Латиница в русском тексте (только если много)
        if len(anomalies['latin_in_russian']) > 10:
            print(f"\n🟡 ЛАТИНИЦА В РУССКОМ ТЕКСТЕ - {len(anomalies['latin_in_russian'])} случаев:")
            print("-"*80)
            for line_num, line in anomalies['latin_in_russian'][:10]:  # Показываем первые 10
                print(f"  Строка {line_num:5d}: {line}...")
            if len(anomalies['latin_in_russian']) > 10:
                print(f"  ... и еще {len(anomalies['latin_in_russian']) - 10} случаев")
        
        # Необычные символы (только если много и нет токенов)
        if anomalies['unusual_symbols'] and not anomalies['tokens'] and len(anomalies['unusual_symbols']) > 20:
            print(f"\n🟠 НЕОБЫЧНЫЕ СИМВОЛЫ - {len(anomalies['unusual_symbols'])} случаев (первые 10):")
            print("-"*80)
            for line_num, line in anomalies['unusual_symbols'][:10]:
                print(f"  Строка {line_num:5d}: {line}...")
    
    print(f"\n{'='*80}")
    print(f"ИТОГО: найдено аномалий в {total_files_with_anomalies} файлах")
    print('='*80)

if __name__ == '__main__':
    main()

