-- 查询'书'字、'颜真卿'和'多宝塔碑'对应的图片详情
SELECT images.id, images.url, glyphs.han, authors.name, books.title
FROM images
JOIN glyphs ON images.glyph_id = glyphs.id
JOIN authors ON glyphs.author_id = authors.id
JOIN books ON glyphs.book_id = books.id
WHERE glyphs.han = '书'
AND authors.name = '颜真卿'
AND books.title = '多宝塔碑';