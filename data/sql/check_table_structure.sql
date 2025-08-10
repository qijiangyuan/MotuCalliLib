-- 查看glyphs表结构
SELECT sql FROM sqlite_master WHERE type='table' AND name='glyphs';

-- 查看images表结构
SELECT sql FROM sqlite_master WHERE type='table' AND name='images';

-- 查看authors表结构
SELECT sql FROM sqlite_master WHERE type='table' AND name='authors';

-- 查看books表结构
SELECT sql FROM sqlite_master WHERE type='table' AND name='books';