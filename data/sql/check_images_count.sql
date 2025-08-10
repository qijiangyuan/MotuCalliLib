-- 查询颜真卿的author_id
SELECT id FROM authors WHERE name = '颜真卿';

-- 查询多宝塔碑的book_id
SELECT id FROM books WHERE title = '多宝塔碑';

-- 查询'书'字的glyph_id
SELECT id FROM glyphs WHERE han = '书';

-- 统计对应图片数量
SELECT COUNT(*) FROM images
JOIN glyphs ON images.glyph_id = glyphs.id
WHERE glyphs.han = '书'
AND glyphs.book_id = (SELECT id FROM books WHERE title = '多宝塔碑')
AND glyphs.author_id = (SELECT id FROM authors WHERE name = '颜真卿');