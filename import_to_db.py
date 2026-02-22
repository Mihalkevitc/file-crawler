import sqlite3
import csv
import os

def init_db(db_path='database/files.db'):
    """
    Создаём базу данных с двумя таблицами:
    - files: основное хранилище
    - files_fts: виртуальная таблица для полнотекстового поиска
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            content TEXT
        )
    ''')
    
    c.execute('''
        CREATE VIRTUAL TABLE files_fts USING fts5(
            file_name, content,
            content=files,
            content_rowid=id
        )
    ''')
    
    c.execute('''
        CREATE TRIGGER files_ai AFTER INSERT ON files BEGIN
            INSERT INTO files_fts(rowid, file_name, content)
            VALUES (new.id, new.file_name, new.content);
        END;
    ''')
    
    conn.commit()
    conn.close()

def import_csv(csv_file='output/file_index.csv', db_file='database/files.db'):
    """Загружаем данные из CSV в базу"""
    if not os.path.exists(csv_file):
        return
    
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            c.execute('''
                INSERT INTO files (file_path, file_name, file_type, file_size, content)
                VALUES (?, ?, ?, ?, ?)
            ''', (row['file_path'], row['file_name'], row['file_type'],
                  int(row['file_size']) if row['file_size'] else 0,
                  row['content'][:10000]))
    
    conn.commit()
    conn.close()

def search(query, db_file='database/files.db'):
    """Ищем по базе с использованием FTS5"""
    if not os.path.exists(db_file):
        return []
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    c.execute('''
        SELECT f.file_name, f.file_path, snippet(files_fts, 1, '<b>', '</b>', '...', 15)
        FROM files_fts JOIN files f ON files_fts.rowid = f.id
        WHERE files_fts MATCH ?
        ORDER BY rank
        LIMIT 10
    ''', (f'"{query}"',))
    
    results = c.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    import_csv()
    
    for term in ['инвестиции', 'налог', 'компания', 'финансы']:
        print(f"\nПоиск: {term}")
        for r in search(term):
            print(f"  {r[0]} - {r[2]}")