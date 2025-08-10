let page = 1;
let total = 0;
let per_page = 24;  // 默认每页显示6行4列共24个结果
let currentQuery = {};
let isShowingAll = false; // 标记是否显示全部结果

document.addEventListener("DOMContentLoaded", () => {
    // 确保分页容器在页面加载时处于隐藏状态
    document.getElementById("paginationContainer").style.display = "none";
    console.log('页面加载完成 - 分页容器初始状态: 隐藏');
    loadOptions();
    document.getElementById("searchForm").addEventListener("submit", e => {
        e.preventDefault();
        page = 1;
        isShowingAll = false; // 重置为默认显示
        document.getElementById("results").innerHTML = "";
        currentQuery = Object.fromEntries(new FormData(e.target).entries());
        search();
        // 生成汉字按钮
        generateHanziButtons(currentQuery.han);
    });

    // 添加汉字输入框事件监听
    const hanInput = document.getElementById("hanInput");
    if (hanInput) {
        hanInput.addEventListener("input", function() {
            const inputValue = this.value.trim();
            generateHanziButtons(inputValue);
        });
    }

    // 点击汉字按钮时触发搜索
    document.getElementById("hanziButtons").addEventListener("click", function(e) {
        if (e.target.classList.contains("hanzi-btn")) {
            // 移除所有按钮的高亮状态
            document.querySelectorAll(".hanzi-btn").forEach(btn => {
                btn.classList.remove("btn-primary");
                btn.classList.add("btn-outline-primary");
            });
            // 高亮当前点击的按钮
            e.target.classList.remove("btn-outline-primary");
            e.target.classList.add("btn-primary");
            // 获取按钮上的汉字
            const han = e.target.textContent;
            // 执行搜索
            page = 1;
            isShowingAll = false;
            document.getElementById("results").innerHTML = "";
            currentQuery.han = han;
            search();
        }
    });
    document.getElementById("prevPageBtn").addEventListener("click", (e) => {
        e.preventDefault();
        if (page > 1) {
            page--;
            document.getElementById("results").innerHTML = "";
            search();
        }
    });
    document.getElementById("nextPageBtn").addEventListener("click", (e) => {
        e.preventDefault();
        if (page * per_page < total) {
            page++;
            document.getElementById("results").innerHTML = "";
            search();
        }
    });
});

// 初始化函数，在页面加载完成后执行
function init() {
    // 清空汉字按钮区域
    const buttonsContainer = document.getElementById("hanziButtons");
    if (buttonsContainer) {
        buttonsContainer.innerHTML = "";
    }
}

function loadOptions() {
    fetch("/api/options")
        .then(res => res.json())
        .then(data => {
            fillSelect("font", data.fonts);
            
            // 初始化书法家选择框
            const authorSelect = document.getElementById('authorSelect');
            $(authorSelect).empty();
            $(authorSelect).append($('<option>', {value: '', text: '书法家'}));
            data.authors.forEach(author => {
                $(authorSelect).append($('<option>', {value: author, text: author}));
            });
            $(authorSelect).select2({
                placeholder: '书法家',
                allowClear: true,
                width: '100%'
            });
            
            // 初始化出处选择框
            const bookSelect = document.getElementById('bookSelect');
            $(bookSelect).empty();
            $(bookSelect).append($('<option>', {value: '', text: '来源典籍'}));
            data.books.forEach(book => {
                $(bookSelect).append($('<option>', {value: book, text: book}));
            });
            $(bookSelect).select2({
                placeholder: '来源典籍',
                allowClear: true,
                width: '100%'
            });
        });
}

// 保留字体下拉框的填充函数
function fillSelect(name, options) {
    const select = document.querySelector(`[name="${name}"]`);
    select.innerHTML = '<option value="">字体</option>';
    options.forEach(opt => {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = opt;
        select.appendChild(o);
    });
    
    // 初始化select2
    $(select).select2({
        placeholder: '字体',
        allowClear: true,
        width: '100%'
    });
}

// 生成汉字按钮的函数
function generateHanziButtons(hanzi) {
    const buttonsContainer = document.getElementById("hanziButtons");
    buttonsContainer.innerHTML = "";

    if (!hanzi || hanzi.length === 0) {
        return;
    }

    // 去重并保持顺序
    const uniqueChars = [...new Set(hanzi.split(''))];

    uniqueChars.forEach(char => {
        const button = document.createElement("button");
        button.className = "hanzi-btn btn btn-outline-primary";
        button.textContent = char;
        button.style.margin = "4px";
        button.style.padding = "8px 16px";
        button.style.fontSize = "18px";
        buttonsContainer.appendChild(button);
    });
}

function search(append=false) {
    document.getElementById("loading").style.display = "block";

    // 构建查询参数
            const queryParams = {...currentQuery};
            
            // 如果正在显示全部结果
            if (isShowingAll) {
                queryParams.all = true;
                page = 1; // 重置为第一页
            } else {
                queryParams.page = page;
                queryParams.per_page = per_page; // 添加每页数量参数
            }

    const params = new URLSearchParams(queryParams);
    fetch("/api/search?" + params.toString())
        .then(res => res.json())
        .then(data => {
            total = data.total;
            per_page = data.per_page || 4; // 确保有默认值
            renderResults(data.results, append);
            document.getElementById("loading").style.display = "none";            
            // 显示分页容器
            // 只有当有结果、不是显示全部且总页数大于1时才显示分页
            const totalPages = Math.ceil(total / per_page);
            console.log('search() - 分页显示判断:');
            console.log('total > 0:', total > 0);
            console.log('!isShowingAll:', !isShowingAll);
            console.log('totalPages > 1:', totalPages > 1);
            if (total > 0 && !isShowingAll && totalPages > 1) {
            // 只在满足条件时显示分页
            document.getElementById("paginationContainer").style.display = "block";
            console.log('分页容器已显示');
        } else {
            document.getElementById("paginationContainer").style.display = "none";
            console.log('分页容器已隐藏');
                // 确保所有分页元素都被隐藏
                document.getElementById("prevPageBtn").style.display = "none";
                document.getElementById("nextPageBtn").style.display = "none";
                document.getElementById("firstPageBtn").style.display = "none";
                document.getElementById("ellipsisStart").style.display = "none";
                document.getElementById("pageNumbers").innerHTML = "";
                document.getElementById("pageNumbersContainer").style.display = "none";
                document.getElementById("ellipsisEnd").style.display = "none";
                document.getElementById("lastPageBtn").style.display = "none";
            }
            
            // 更新分页按钮状态
            if (!isShowingAll) {
                // 显示/隐藏上一页按钮
                if (page > 1) {
                    document.getElementById("prevPageBtn").style.display = "inline-block";
                } else {
                    document.getElementById("prevPageBtn").style.display = "none";
                }
                
                // 显示/隐藏下一页按钮
                if (page * per_page < total) {
                    document.getElementById("nextPageBtn").style.display = "inline-block";
                } else {
                    document.getElementById("nextPageBtn").style.display = "none";
                }
                
                // 计算总页数
                const totalPages = Math.ceil(total / per_page);
                
                // 更新移动设备上的页码信息
                // 已删除pageInfo元素的引用
                
                // 生成页码按钮
                generatePageNumbers(totalPages);
            } else {
                // 显示全部结果时隐藏分页导航
                document.getElementById("paginationContainer").style.display = "none";
                document.getElementById("prevPageBtn").style.display = "none";
                document.getElementById("nextPageBtn").style.display = "none";
                document.getElementById("firstPageBtn").style.display = "none";
                document.getElementById("ellipsisStart").style.display = "none";
                document.getElementById("pageNumbers").innerHTML = "";
                document.getElementById("ellipsisEnd").style.display = "none";
                document.getElementById("lastPageBtn").style.display = "none";
                // 已删除pageInfo元素的引用
            }
        });
}

// 生成页码按钮
function generatePageNumbers(totalPages) {
    const pageNumbersContainer = document.getElementById("pageNumbers");
    pageNumbersContainer.innerHTML = "";
    
    // 设置最后一页按钮文本
    const lastPageBtn = document.getElementById("lastPageBtn");
    lastPageBtn.querySelector("a").textContent = totalPages;
    
    // 显示/隐藏分页控制元素 - 严格控制只有在有结果且非显示全部时才显示
    console.log('generatePageNumbers() - 分页显示判断:');
    console.log('total > 0:', total > 0);
    console.log('!isShowingAll:', !isShowingAll);
    console.log('totalPages > 1:', totalPages > 1);
    if (total > 0 && !isShowingAll && totalPages > 1) {
            // 只在满足条件时显示分页
            document.getElementById("paginationContainer").style.display = "block";
            console.log('generatePageNumbers() - 分页容器已显示');
        } else {
            document.getElementById("paginationContainer").style.display = "none";
            console.log('generatePageNumbers() - 分页容器已隐藏');
            // 确保所有分页元素都被隐藏
            document.getElementById("prevPageBtn").style.display = "none";
            document.getElementById("nextPageBtn").style.display = "none";
            document.getElementById("firstPageBtn").style.display = "none";
            document.getElementById("ellipsisStart").style.display = "none";
            document.getElementById("pageNumbers").innerHTML = "";
            document.getElementById("pageNumbersContainer").style.display = "none";
            document.getElementById("ellipsisEnd").style.display = "none";
            document.getElementById("lastPageBtn").style.display = "none";
            return;
        }
    
    // 根据条件控制上下页按钮的显示
            document.getElementById("prevPageBtn").style.display = page > 1 ? "inline-block" : "none";
            document.getElementById("nextPageBtn").style.display = page < totalPages ? "inline-block" : "none";
    
    // 禁用/启用上下页按钮
    document.getElementById("prevPageBtn").classList.toggle("disabled", page === 1);
    document.getElementById("nextPageBtn").classList.toggle("disabled", page === totalPages);
    
    // 强制隐藏所有可能导致问题的元素
    document.getElementById("firstPageBtn").style.display = "none";
    document.getElementById("lastPageBtn").style.display = "none";
    document.getElementById("ellipsisStart").style.display = "none";
    document.getElementById("ellipsisEnd").style.display = "none";
    
    // 显示页码容器
    document.getElementById("pageNumbersContainer").style.display = "inline-block";
    
    // 只在总页数>8时才显示首尾页和省略号
    if (totalPages > 8) {
        document.getElementById("firstPageBtn").style.display = "inline-block";
        document.getElementById("lastPageBtn").style.display = "inline-block";
        
        // 显示/隐藏省略号
        document.getElementById("ellipsisStart").style.display = page > 4 ? "inline-block" : "none";
        document.getElementById("ellipsisEnd").style.display = page < totalPages - 3 ? "inline-block" : "none";
        
        // 确定页码范围
        let startPage = Math.max(2, page - 3); // 从2开始，因为1是首页
        let endPage = Math.min(totalPages - 1, page + 3); // 到totalPages-1结束，因为totalPages是末页
        
        // 调整范围以确保显示5个页码
        if (endPage - startPage < 4) {
            if (startPage === 2) {
                endPage = Math.min(6, totalPages - 1);
            } else if (endPage === totalPages - 1) {
                startPage = Math.max(2, totalPages - 5);
            }
        }
        
        // 生成中间的页码按钮
        for (let i = startPage; i <= endPage; i++) {
            const li = document.createElement("li");
            li.style.display = "inline-block";
            li.className = `page-item ${i === page ? 'active' : ''}`;
            
            const a = document.createElement("a");
            a.className = "page-link";
            a.href = "#";
            a.textContent = i;
            
            a.addEventListener("click", (e) => {
                e.preventDefault();
                if (i !== page) {
                    page = i;
                    document.getElementById("results").innerHTML = "";
                    search();
                }
            });
            
            li.appendChild(a);
            pageNumbersContainer.appendChild(li);
        }
    } else {
        // 总页数<=8时，显示所有页码
        for (let i = 1; i <= totalPages; i++) {
            const li = document.createElement("li");
            li.style.display = "inline-block";
            li.className = `page-item ${i === page ? 'active' : ''}`;
            
            const a = document.createElement("a");
            a.className = "page-link";
            a.href = "#";
            a.textContent = i;
            
            a.addEventListener("click", (e) => {
                e.preventDefault();
                if (i !== page) {
                    page = i;
                    document.getElementById("results").innerHTML = "";
                    search();
                }
            });
            
            li.appendChild(a);
            pageNumbersContainer.appendChild(li);
        }
    }     
    
    // 已删除pageInfo元素，不再更新页码信息
    
    // 添加第一页和最后一页的点击事件
    document.getElementById("firstPageBtn").querySelector("a").addEventListener("click", (e) => {
        e.preventDefault();
        if (page !== 1) {
            page = 1;
            document.getElementById("results").innerHTML = "";
            search();
        }
    });
    
    document.getElementById("lastPageBtn").querySelector("a").addEventListener("click", (e) => {
        e.preventDefault();
        if (page !== totalPages) {
            page = totalPages;
            document.getElementById("results").innerHTML = "";
            search();
        }
    });
}

function renderResults(items, append) {
    const container = document.getElementById("results");
    if (!append) container.innerHTML = "";

    items.forEach(item => {
        const col = document.createElement("div");
            col.className = "col-md-3";
        // 创建卡片容器
            const card = document.createElement('div');
            card.className = 'glyph-card';

            // 创建文字信息
            const hanDiv = document.createElement('div');
            hanDiv.textContent = item.han;
            card.appendChild(hanDiv);

            // 创建作者信息
            const infoSmall = document.createElement('small');
            infoSmall.textContent = `${item.font} | ${item.author} | ${item.book_title || ''}`;
            card.appendChild(infoSmall);

            // 创建图片容器
            const imgContainer = document.createElement('div');
            imgContainer.style.display = 'flex';
            imgContainer.style.flexWrap = 'wrap';
            imgContainer.style.justifyContent = 'center';
            card.appendChild(imgContainer);

            // 创建查看更多按钮
            const showMoreBtn = document.createElement('button');
            showMoreBtn.className = 'btn btn-sm btn-outline-primary mt-2';
            showMoreBtn.textContent = '查看更多';
            showMoreBtn.style.display = 'none';
            showMoreBtn.onclick = function() {
                // 在新窗口中打开查看所有图片页面
                window.open(`/view_all_images.html?glyph_id=${item.id}&han=${encodeURIComponent(item.han)}&author=${encodeURIComponent(item.author)}&book=${encodeURIComponent(item.book_title || '')}`, '_blank');
            };
            card.appendChild(showMoreBtn);

            col.appendChild(card);

            // 异步加载图片，默认只显示1张
            fetch(`/images/${item.id}`)
                .then(res => res.json())
                .then(data => {
                    if (data.image_urls && data.image_urls.length > 0) {
                        // 只显示第一张图片
                        const img = document.createElement('img');
                        img.className = 'glyph-img';
                        img.alt = item.han;
                        img.src = data.image_urls[0];
                        imgContainer.appendChild(img);

                        // 始终显示查看更多按钮，即使只有一张图片
                        showMoreBtn.style.display = 'inline-block';
                    }
                })
                .catch(error => {
                    console.error('加载图片失败:', error);
                });
        container.appendChild(col);
    });
}

// 加载所有图片的函数
function loadAllImages(glyphId, container) {
    fetch(`/images/${glyphId}`)
        .then(res => res.json())
        .then(data => {
            if (data.image_urls && data.image_urls.length > 0) {
                data.image_urls.forEach(url => {
                    const img = document.createElement('img');
                    img.className = 'glyph-img';
                    img.alt = '书法字';
                    img.src = url;
                    img.style.margin = '4px';
                    img.style.maxWidth = 'calc(50% - 8px)';
                    container.appendChild(img);
                });
            }
        })
        .catch(error => {
            console.error('加载图片失败:', error);
        });
}