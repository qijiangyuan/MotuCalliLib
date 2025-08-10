-- 附加旧库
ATTACH DATABASE 'shufa.db' AS olddb;

-- 创建新表结构
CREATE TABLE fonts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE
);

CREATE TABLE glyphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    han TEXT,
    font_id INTEGER,
    author_id INTEGER,
    book_id INTEGER,
    FOREIGN KEY(font_id) REFERENCES fonts(id),
    FOREIGN KEY(author_id) REFERENCES authors(id),
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    glyph_id INTEGER,
    url TEXT,
    FOREIGN KEY(glyph_id) REFERENCES glyphs(id)
);

-- 插入维度表（去重）
INSERT INTO fonts (name)
SELECT DISTINCT font FROM olddb.shufa WHERE font IS NOT NULL;

INSERT INTO authors (name)
SELECT DISTINCT author FROM olddb.shufa WHERE author IS NOT NULL;

INSERT INTO books (title)
SELECT DISTINCT book FROM olddb.shufa WHERE book IS NOT NULL;

-- 插入 glyphs 表（JOIN + DISTINCT 防止重复）
INSERT INTO glyphs (han, font_id, author_id, book_id)
SELECT DISTINCT
    s.han,
    f.id AS font_id,
    a.id AS author_id,
    b.id AS book_id
FROM olddb.shufa s
LEFT JOIN fonts f ON s.font = f.name
LEFT JOIN authors a ON s.author = a.name
LEFT JOIN books b ON s.book = b.title
WHERE s.han IS NOT NULL;

-- 插入 images 表（保留重复图片，移除DISTINCT）
INSERT INTO images (glyph_id, url)
SELECT
    g.id AS glyph_id,
    s.image AS url
FROM olddb.shufa s
JOIN fonts f ON s.font = f.name
JOIN authors a ON s.author = a.name
JOIN books b ON s.book = b.title
JOIN glyphs g ON g.han = s.han
              AND g.font_id = f.id
              AND g.author_id = a.id
              AND g.book_id = b.id
WHERE s.image IS NOT NULL;

-- 创建索引（移除images表的唯一索引）
CREATE UNIQUE INDEX idx_glyphs_unique ON glyphs(han, font_id, author_id, book_id);

CREATE INDEX idx_han ON glyphs(han);
CREATE INDEX idx_han_font ON glyphs(han, font_id);
CREATE INDEX idx_font_id ON glyphs(font_id);
CREATE INDEX idx_author_id ON glyphs(author_id);
CREATE INDEX idx_images_glyph ON images(glyph_id);

-- 完成
DETACH DATABASE olddb;