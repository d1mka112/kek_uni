#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска аномалий в текстовых файлах с произведениями русской литературы.
Ищет токены, лишние непонятные символы (не названия глав), и другие аномалии.
"""

import os
import re
import sys
from pathlib import Path

# Кириллица, цифры, основные знаки препинания, пробельные символы
RUSSIAN_CHARS = set('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя0123456789')
PUNCTUATION = set('.,;:!?-"()[]{}«»—–…')
WHITESPACE = set(' \n\r\t')
ALLOWED_CHARS = RUSSIAN_CHARS | PUNCTUATION | WHITESPACE

# Паттерны для названий глав (римские цифры, слова ГЛАВА, ЧАСТЬ и т.д.)
CHAPTER_PATTERNS = [
    r'^[IVXLCDM]+$',  # Римские цифры
    r'^ГЛАВА\s+[IVXLCDM\d]+',  # ГЛАВА I, ГЛАВА 1
    r'^ЧАСТЬ\s+[IVXLCDM\d]+',  # ЧАСТЬ I, ЧАСТЬ 1
    r'^[ГЧ]\s*[IVXLCDM\d]+',  # Г I, Ч 1
    r'^\d+$',  # Просто число (могут быть номера глав)
]

def is_likely_chapter_title(line):
    """Проверяет, является ли строка названием главы"""
    stripped = line.strip()
    if not stripped:
        return False
    
    for pattern in CHAPTER_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    
    # Проверка на короткие строки, состоящие только из заглавных букв
    if len(stripped) < 30 and stripped.isupper() and stripped.replace(' ', '').isalpha():
        return True
    
    return False

def find_anomalies_in_line(line, line_num):
    """Находит аномалии в строке"""
    anomalies = []
    
    # Пропускаем пустые строки и названия глав
    if not line.strip() or is_likely_chapter_title(line):
        return anomalies
    
    # Проверяем наличие недопустимых символов
    suspicious_chars = []
    for i, char in enumerate(line):
        if char not in ALLOWED_CHARS:
            suspicious_chars.append((i, char, ord(char)))
    
    if suspicious_chars:
        # Проверяем, не является ли это латиницей (которая может быть в именах собственных)
        has_russian = any(c in RUSSIAN_CHARS for c in line)
        
        # Если в строке есть кириллица, но также есть латиница - это аномалия
        if has_russian:
            latin_chars = [(i, c) for i, c, _ in suspicious_chars if c.isalpha() and ord(c) < 128]
            if latin_chars:
                anomalies.append({
                    'type': 'latin_in_russian',
                    'line_num': line_num,
                    'chars': latin_chars,
                    'line': line.strip()[:200]  # Первые 200 символов
                })
            
            # Другие подозрительные символы (не латиница, не кириллица)
            other_chars = [(i, c, hex(ord(c))) for i, c, code in suspicious_chars 
                          if not (c.isalpha() and ord(c) < 128)]
            if other_chars:
                anomalies.append({
                    'type': 'unusual_symbols',
                    'line_num': line_num,
                    'chars': other_chars,
                    'line': line.strip()[:200]
                })
    
    # Проверяем строки, которые содержат много латиницы без кириллицы (токены?)
    if not any(c in RUSSIAN_CHARS for c in line) and line.strip():
        latin_count = sum(1 for c in line if c.isalpha() and ord(c) < 128)
        if latin_count > 10:  # Больше 10 латинских символов без кириллицы
            anomalies.append({
                'type': 'token_like',
                'line_num': line_num,
                'line': line.strip()[:200]
            })
    
    # Проверяем строки с множеством подряд идущих необычных символов
    if re.search(r'[^\w\s\u0400-\u04FF.,;:!?\-"()\[\]{}«»—–…]{3,}', line):
        anomalies.append({
            'type': 'multiple_unusual_chars',
            'line_num': line_num,
            'line': line.strip()[:200]
        })
    
    return anomalies

def analyze_file(filepath):
    """Анализирует файл на наличие аномалий"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='cp1251') as f:
                lines = f.readlines()
        except Exception as e:
            return {'error': f'Не удалось прочитать файл: {e}'}
    except Exception as e:
        return {'error': f'Ошибка при чтении файла: {e}'}
    
    all_anomalies = []
    for line_num, line in enumerate(lines, 1):
        anomalies = find_anomalies_in_line(line, line_num)
        all_anomalies.extend(anomalies)
    
    return {
        'total_lines': len(lines),
        'anomalies': all_anomalies
    }

def main():
    script_dir = Path(__file__).parent
    txt_files = list(script_dir.glob('*.txt'))
    
    if not txt_files:
        print("Не найдено .txt файлов в директории")
        return
    
    print(f"Найдено {len(txt_files)} .txt файлов\n")
    print("=" * 80)
    
    files_with_anomalies = []
    
    for txt_file in sorted(txt_files):
        result = analyze_file(txt_file)
        
        if 'error' in result:
            print(f"\n❌ {txt_file.name}")
            print(f"   Ошибка: {result['error']}")
            continue
        
        anomalies = result['anomalies']
        
        if anomalies:
            files_with_anomalies.append((txt_file.name, anomalies))
            print(f"\n🔍 {txt_file.name} ({result['total_lines']} строк)")
            
            # Группируем аномалии по типам
            by_type = {}
            for anomaly in anomalies:
                a_type = anomaly['type']
                if a_type not in by_type:
                    by_type[a_type] = []
                by_type[a_type].append(anomaly)
            
            for a_type, type_anomalies in by_type.items():
                print(f"\n   Тип аномалии: {a_type} ({len(type_anomalies)} случаев)")
                
                # Показываем первые 5 примеров каждого типа
                for anomaly in type_anomalies[:5]:
                    print(f"      Строка {anomaly['line_num']}: {anomaly['line'][:100]}...")
                
                if len(type_anomalies) > 5:
                    print(f"      ... и еще {len(type_anomalies) - 5} случаев")
        
        # Показываем прогресс для файлов без аномалий
        # (раскомментируйте, если хотите видеть все файлы)
        # else:
        #     print(f"✓ {txt_file.name} - аномалий не найдено")
    
    print("\n" + "=" * 80)
    print(f"\nИтого: найдено {len(files_with_anomalies)} файлов с аномалиями из {len(txt_files)} проверенных")
    
    # Сохраняем детальный отчет в файл
    report_file = script_dir / 'anomalies_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ ОБ АНОМАЛИЯХ В ТЕКСТОВЫХ ФАЙЛАХ\n")
        f.write("=" * 80 + "\n\n")
        
        for filename, anomalies in files_with_anomalies:
            f.write(f"\n{'='*80}\n")
            f.write(f"Файл: {filename}\n")
            f.write(f"Всего аномалий: {len(anomalies)}\n")
            f.write(f"{'='*80}\n\n")
            
            by_type = {}
            for anomaly in anomalies:
                a_type = anomaly['type']
                if a_type not in by_type:
                    by_type[a_type] = []
                by_type[a_type].append(anomaly)
            
            for a_type, type_anomalies in by_type.items():
                f.write(f"\nТип: {a_type} ({len(type_anomalies)} случаев)\n")
                f.write("-" * 80 + "\n")
                
                for anomaly in type_anomalies:
                    f.write(f"\nСтрока {anomaly['line_num']}:\n")
                    f.write(f"{anomaly['line']}\n")
                    
                    if 'chars' in anomaly:
                        f.write(f"Подозрительные символы: {anomaly['chars']}\n")
    
    print(f"\nДетальный отчет сохранен в: {report_file}")

if __name__ == '__main__':
    main()


