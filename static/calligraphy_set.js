document.addEventListener("DOMContentLoaded", () => {
    // 加载选项（字体、书法家、典籍）
    loadOptions();

    // 添加事件监听器
    document.getElementById("generateBtn").addEventListener("click", generateCalligraphy);
    document.getElementById("clearBtn").addEventListener("click", clearContent);
    document.getElementById("saveBtn").addEventListener("click", saveCalligraphy);
    document.getElementById("exportBtn").addEventListener("click", exportAsImage);
});

// 加载选项（字体、书法家、典籍）
function loadOptions() {
    fetch("/api/options")
        .then(res => res.json())
        .then(data => {
            // 加载字体选项
            const fontSelect = document.getElementById("fontSelect");
            fontSelect.innerHTML = '<option value="">选择字体</option>';
            data.fonts.forEach(font => {
                const option = document.createElement("option");
                option.value = font;
                option.textContent = font;
                fontSelect.appendChild(option);
            });
            $(fontSelect).select2({
                placeholder: '选择字体',
                allowClear: true,
                width: 'auto'
            });

            // 加载书法家选项
            const calligrapherSelect = document.getElementById("calligrapherSelect");
            calligrapherSelect.innerHTML = '<option value="">选择书法家</option>';
            data.authors.forEach(author => {
                const option = document.createElement("option");
                option.value = author;
                option.textContent = author;
                calligrapherSelect.appendChild(option);
            });
            $(calligrapherSelect).select2({
                placeholder: '选择书法家',
                allowClear: true,
                width: 'auto'
            });

            // 加载典籍选项
            const bookSelect = document.getElementById("bookSelect");
            bookSelect.innerHTML = '<option value="">选择典籍</option>';
            data.books.forEach(book => {
                const option = document.createElement("option");
                option.value = book;
                option.textContent = book;
                bookSelect.appendChild(option);
            });
            $(bookSelect).select2({
                placeholder: '选择典籍',
                allowClear: true,
                width: 'auto'
            });
        });
}

// 生成集字
function generateCalligraphy() {
    const textInput = document.getElementById("textInput").value.trim();
    const fontSelect = document.getElementById("fontSelect").value;
    const directionSelect = document.getElementById("directionSelect").value;
    const charsPerLineInput = document.getElementById("charsPerLineInput").value;
    const calligrapherSelect = document.getElementById("calligrapherSelect").value;
    const bookSelect = document.getElementById("bookSelect").value;

    if (!textInput) {
        alert("请输入文字内容");
        return;
    }

    const resultContainer = document.getElementById("resultContainer");
    resultContainer.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="sr-only">加载中...</span></div>';

    // 构建查询参数
    const queryParams = new URLSearchParams({
        text: textInput,
        font: fontSelect || '',
        direction: directionSelect || 'horizontal',
        chars_per_line: charsPerLineInput || '5',
        calligrapher: calligrapherSelect || '',
        book: bookSelect || ''
    });

    // 调用API生成集字
    fetch("/api/generate_calligraphy?" + queryParams.toString())
        .then(res => res.json())
        .then(data => {
            if (data.success && data.characters) {
                renderCalligraphyResult(data.characters, directionSelect);
            } else {
                resultContainer.innerHTML = '<p class="text-danger">生成失败: ' + (data.message || '未知错误') + '</p>';
            }
        })
        .catch(error => {
            console.error("生成集字失败:", error);
            resultContainer.innerHTML = '<p class="text-danger">生成失败，请重试</p>';
        });
}

// 渲染集字结果
function renderCalligraphyResult(characters, direction) {
    const resultContainer = document.getElementById("resultContainer");
    resultContainer.innerHTML = '';

    const resultDiv = document.createElement("div");
    resultDiv.className = "calligraphy-result";
    resultDiv.style.padding = "20px";

    // 获取每行显示字数
    const charsPerLine = parseInt(document.getElementById("charsPerLineInput").value) || 5;

    // 根据排列方向和每行显示字数设置样式
    if (charsPerLine > 0) {
        // 限制字数时使用Grid布局
        resultDiv.style.width = "100%";
        resultDiv.style.boxSizing = "border-box";
        resultDiv.style.display = "grid";
        resultDiv.style.overflow = "hidden";

        if (direction === 'horizontal') {
            // 从左到右横排
            resultDiv.style.gridTemplateColumns = `repeat(${charsPerLine}, 100px)`;
            resultDiv.style.justifyContent = "start";
            resultDiv.style.gap = "0px";
        } else if (direction === 'horizontal-reverse') {
            // 从右到左横排
            resultDiv.style.gridTemplateColumns = `repeat(${charsPerLine}, 100px)`;
            resultDiv.style.direction = "rtl";
            resultDiv.style.justifyContent = "start";
            resultDiv.style.gap = "0px";
        } else if (direction === 'vertical-left') {
            // 从上到下竖排-左起
            resultDiv.style.gridTemplateColumns = `repeat(auto-fill, 100px)`; // 固定列宽
            resultDiv.style.gridTemplateRows = `repeat(${charsPerLine}, 100px)`; // 固定行高
            resultDiv.style.gridAutoFlow = "column";
            resultDiv.style.justifyItems = "center";
            resultDiv.style.gap = "0px";
        } else if (direction === 'vertical-right') {
            // 从上到下竖排-右起
            resultDiv.style.gridTemplateColumns = `repeat(auto-fill, 100px)`; // 固定列宽
            resultDiv.style.gridTemplateRows = `repeat(${charsPerLine}, 100px)`; // 固定行高
            resultDiv.style.gridAutoFlow = "column";
            resultDiv.style.direction = "rtl";
            resultDiv.style.justifyItems = "center";
            resultDiv.style.gap = "0px";
        }
    } else {
        // 竖排或不限制字数时使用Flex布局
        resultDiv.style.display = "flex";
        if (direction === 'horizontal') {
            // 从左到右横排
            resultDiv.style.flexDirection = "row";
            resultDiv.style.flexWrap = "wrap";
            resultDiv.style.justifyContent = "center";
            resultDiv.style.alignItems = "center";
            resultDiv.style.gap = "0px";
        } else if (direction === 'horizontal-reverse') {
            // 从右到左横排
            resultDiv.style.flexDirection = "row-reverse";
            resultDiv.style.flexWrap = "wrap";
            resultDiv.style.justifyContent = "center";
            resultDiv.style.alignItems = "center";
            resultDiv.style.gap = "0px";
        } else if (direction === 'vertical-left') {
            // 从上到下竖排-左起
            resultDiv.style.flexDirection = "column";
            resultDiv.style.flexWrap = "nowrap";
            resultDiv.style.justifyContent = "center";
            resultDiv.style.alignItems = "flex-start";
            resultDiv.style.gap = "0px";
        } else if (direction === 'vertical-right') {
            // 从上到下竖排-右起
            resultDiv.style.flexDirection = "column";
            resultDiv.style.flexWrap = "nowrap";
            resultDiv.style.justifyContent = "center";
            resultDiv.style.alignItems = "flex-end";
            resultDiv.style.gap = "0px";
        } else {
            // 默认从左到右横排
            resultDiv.style.flexDirection = "row";
            resultDiv.style.flexWrap = "wrap";
            resultDiv.style.justifyContent = "center";
            resultDiv.style.alignItems = "center";
            resultDiv.style.gap = "10px";
        }
    }

    // 对于垂直方向排列，调整字符顺序以确保正确的阅读顺序
    if (direction === 'vertical-left' || direction === 'vertical-right') {
        // 计算实际需要的列数
        const cols = Math.ceil(characters.length / charsPerLine);
        const rearrangedCharacters = [];

        if (direction === 'vertical-left') {
            // vertical-left: 从左上角开始，向下填充，达到字数限制换列
            for (let col = 0; col < cols; col++) {
                for (let row = 0; row < charsPerLine; row++) {
                    const index = col * charsPerLine + row;
                    if (index < characters.length) {
                        rearrangedCharacters.push(characters[index]);
                    }
                }
            }
        } else if (direction === 'vertical-right') {
            // vertical-right: 从右上角开始，向下填充，达到字数限制换列（右到左）
            for (let col = cols - 1; col >= 0; col--) {
                for (let row = 0; row < charsPerLine; row++) {
                    const index = (cols - 1 - col) * charsPerLine + row;
                    if (index < characters.length) {
                        rearrangedCharacters.push(characters[index]);
                    }
                }
            }
        }


        characters = rearrangedCharacters;
    }

    // 对于水平反向排列，反转字符顺序
    if (direction === 'horizontal-reverse') {
        characters = [...characters].reverse();
    }

    characters.forEach(charInfo => {
        if (charInfo.image_urls && charInfo.image_urls.length > 0) {
            const charContainer = document.createElement("div");
            charContainer.className = "char-container glyph-card";
            charContainer.style.display = "flex";
            charContainer.style.flexDirection = "column";
            charContainer.style.alignItems = "center";
            charContainer.style.margin = "0px";
            charContainer.style.position = "relative";

            const img = document.createElement("img");
            img.src = charInfo.image_urls[0];
            img.alt = charInfo.han;
            img.className = 'glyph-img'; // 添加glyph-img类名
            img.style.width = "100%";
            img.style.height = "100%";
            img.style.objectFit = "contain";

            // 创建叠加文字
            const overlayText = document.createElement("div");
            overlayText.className = "char-overlay";
            overlayText.textContent = charInfo.han;

            // 为字符容器添加点击事件
            charContainer.addEventListener('click', function () {
                openCharSelectionModal(charInfo, img);
            });

            charContainer.appendChild(img);
            charContainer.appendChild(overlayText);
            resultDiv.appendChild(charContainer);
        } else {
            const missingChar = document.createElement("div");
            missingChar.className = "missing-char glyph-card";
            missingChar.style.width = "100px";
            missingChar.style.height = "100px";
            missingChar.style.display = "flex";
            missingChar.style.justifyContent = "center";
            missingChar.style.alignItems = "center";
            missingChar.style.border = "1px dashed #ccc";
            missingChar.style.margin = "0px";
            missingChar.style.fontSize = "36px";
            missingChar.style.color = "#999";
            missingChar.textContent = charInfo.han || '?';
            resultDiv.appendChild(missingChar);
        }
    });

    resultContainer.appendChild(resultDiv);
}

// 清空内容
function clearContent() {
    document.getElementById("textInput").value = '';
    document.getElementById("resultContainer").innerHTML = '<p class="text-muted">请输入文字并点击生成按钮</p>';
    $(document.getElementById("fontSelect")).val('').trigger('change');
}

// 添加模态窗口样式
const style = document.createElement('style');
style.textContent = `
.modal {
    display: none;
    position: fixed;
    z-index: 1050;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: auto;
    background-color: rgba(0,0,0,0.5);
}

.modal-content {
    background-color: #fefefe;
    margin: 15% auto;
    padding: 20px;
    border: 1px solid #888;
    width: 80%;
    max-width: 600px;
    border-radius: 8px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}

.close {
    color: #aaa;
    float: right;
    font-size: 28px;
    font-weight: bold;
}

.close:hover,
.close:focus {
    color: black;
    text-decoration: none;
    cursor: pointer;
}

.form-control {
    width: 100%;
    padding: 8px 12px;
    margin: 8px 0;
    box-sizing: border-box;
    border: 1px solid #ccc;
    border-radius: 4px;
}

label {
    font-weight: bold;
}
`;
document.head.appendChild(style);

// 打开字符选择模态窗口
// 打开字符选择模态窗口
function openCharSelectionModal(charInfo, imgElement) {
    // 检查是否已存在模态窗口，如果存在则移除
    const existingModal = document.getElementById('charSelectionModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 创建模态窗口
    const modal = document.createElement('div');
    modal.id = 'charSelectionModal';
    modal.className = 'modal';
    modal.style.display = 'block'; // 确保模态窗口显示

    // 创建模态内容
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.backgroundColor = '#fff';
    modalContent.style.borderRadius = '8px';
    modalContent.style.width = '80%';
    modalContent.style.maxWidth = '600px';
    modalContent.style.padding = '20px';
    modalContent.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.3)';

    // 模态标题
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    modalHeader.style.display = 'flex';
    modalHeader.style.justifyContent = 'space-between';
    modalHeader.style.alignItems = 'center';
    modalHeader.style.marginBottom = '15px';

    const modalTitle = document.createElement('h5');
    modalTitle.className = 'modal-title';
    modalTitle.textContent = `选择 ${charInfo.han} 书法风格`;
    modalTitle.style.margin = '0';

    // 创建关闭按钮
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'close';
    closeButton.style.fontSize = '24px';
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.cursor = 'pointer';
    closeButton.textContent = '×';
    closeButton.onclick = function () {
        modal.remove();
    };

    modalHeader.appendChild(modalTitle);
    modalHeader.appendChild(closeButton);
    modalContent.appendChild(modalHeader);

    // 创建模态体
    const modalBody = document.createElement('div');
    modalBody.className = 'modal-body';

    // 添加书法家选择
    const calligrapherDiv = document.createElement('div');
    calligrapherDiv.style.marginBottom = '15px';

    const calligrapherLabel = document.createElement('label');
    calligrapherLabel.textContent = '选择书法家:';
    calligrapherLabel.style.display = 'block';
    calligrapherLabel.style.marginBottom = '5px';

    const calligrapherSelect = document.createElement('select');
    calligrapherSelect.id = 'modalCalligrapherSelect';
    calligrapherSelect.className = 'form-control';
    calligrapherSelect.innerHTML = '<option value="">选择书法家</option>';

    calligrapherDiv.appendChild(calligrapherLabel);
    calligrapherDiv.appendChild(calligrapherSelect);
    modalBody.appendChild(calligrapherDiv);

    // 添加典籍选择
    const bookDiv = document.createElement('div');
    bookDiv.style.marginBottom = '15px';

    const bookLabel = document.createElement('label');
    bookLabel.textContent = '选择典籍:';
    bookLabel.style.display = 'block';
    bookLabel.style.marginBottom = '5px';

    const bookSelect = document.createElement('select');
    bookSelect.id = 'modalBookSelect';
    bookSelect.className = 'form-control';
    bookSelect.innerHTML = '<option value="">选择典籍</option>';

    bookDiv.appendChild(bookLabel);
    bookDiv.appendChild(bookSelect);
    modalBody.appendChild(bookDiv);

    // 图片展示区域
    const imageContainer = document.createElement('div');
    imageContainer.id = 'imageContainer';
    imageContainer.style.display = 'flex';
    imageContainer.style.flexWrap = 'wrap';
    imageContainer.style.gap = '10px';
    imageContainer.style.marginTop = '15px';

    // 确保模态窗口已添加到文档
    console.log('模态窗口创建中...');

    // 从数据库加载书法家和典籍选项
    console.log('开始加载选项...');
    fetch('/api/options')
        .then(res => {
            console.log('api/options响应状态:', res.status);
            if (!res.ok) {
                throw new Error(`HTTP错误! 状态码: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log('成功获取选项数据:', data);
            // 加载书法家选项
            if (data.authors && Array.isArray(data.authors)) {
                console.log('加载书法家选项数量:', data.authors.length);
                data.authors.forEach(author => {
                    const option = document.createElement('option');
                    option.value = author;
                    option.textContent = author;
                    calligrapherSelect.appendChild(option);
                });
            } else {
                console.error('data.authors不是有效的数组');
            }
            // 初始化Select2
            console.log('初始化书法家Select2...');
            $(calligrapherSelect).select2({
                placeholder: '选择书法家',
                allowClear: true,
                width: '100%'
            }).on('select2:select select2:clear', function () {
                const selectedCalligrapher = $(this).val() || '';
                const selectedBook = $(bookSelect).val() || '';
                console.log('书法家选择已变更:', selectedCalligrapher);
                console.log('当前典籍选择:', selectedBook);
                loadImages(selectedCalligrapher, selectedBook);
            });

            // 加载典籍选项
            if (data.books && Array.isArray(data.books)) {
                console.log('加载典籍选项数量:', data.books.length);
                data.books.forEach(book => {
                    const option = document.createElement('option');
                    option.value = book;
                    option.textContent = book;
                    bookSelect.appendChild(option);
                });
            } else {
                console.error('data.books不是有效的数组');
            }
            console.log('初始化典籍Select2...');
            $(bookSelect).select2({
                placeholder: '选择典籍',
                allowClear: true,
                width: '100%'
            }).on('select2:select select2:clear', function () {
                const selectedCalligrapher = $(calligrapherSelect).val() || '';
                const selectedBook = $(this).val() || '';
                console.log('典籍选择已变更:', selectedBook);
                console.log('当前书法家选择:', selectedCalligrapher);
                loadImages(selectedCalligrapher, selectedBook);
            });

            // 添加查询按钮
            console.log('添加查询按钮...');
            const queryButton = document.createElement('button');
            queryButton.type = 'button';
            queryButton.className = 'btn btn-primary';
            queryButton.textContent = '查询';
            queryButton.style.marginTop = '15px';
            queryButton.onclick = function () {
                // 获取选中的值
                const selectedCalligrapher = $(calligrapherSelect).val() || '';
                const selectedBook = $(bookSelect).val() || '';

                // 添加详细调试日志
                console.log('查询按钮被点击:');
                console.log('- 书法家:', selectedCalligrapher);
                console.log('- 典籍:', selectedBook);
                console.log('- 字符:', charInfo.han);

                // 确保参数正确传递
                if (selectedCalligrapher) {
                    console.log('已选择书法家，将传递给API');
                } else {
                    console.log('未选择书法家，API将返回所有书法家的相关图片');
                }

                // 调用加载图片函数
                loadImages(selectedCalligrapher, selectedBook);
            };
            modalBody.appendChild(queryButton);

            // 初始化后手动触发一次查询
            console.log('初始化后手动触发一次查询');
            loadImages('', '');
        })
        .catch(error => {
            console.error('加载选项时出错:', error);
        });

    // 确保模态窗口已添加到文档后再进行操作
    setTimeout(function () {
        console.log('模态窗口已添加到文档');
    }, 500);

    // 加载图片函数
    function loadImages(calligrapher, book) {
        // 添加详细调试日志
        console.log('调用loadImages函数:');
        console.log('- 书法家参数:', calligrapher);
        console.log('- 典籍参数:', book);
        console.log('- 字符:', charInfo.han);

        // 清空现有图片
        imageContainer.innerHTML = '';

        // 显示加载中
        const loading = document.createElement('div');
        loading.className = 'spinner-border text-primary';
        loading.role = 'status';
        loading.style.margin = '0 auto';
        loading.innerHTML = '<span class="sr-only">加载中...</span>';
        imageContainer.appendChild(loading);

        // 构建查询参数
        const queryParams = new URLSearchParams({
            han: charInfo.han,
            calligrapher: calligrapher || '',
            book: book || ''
        });

        // 打印完整的API请求URL
        const apiUrl = '/api/search?' + queryParams.toString();
        console.log('API请求URL:', apiUrl);

        // 调用API加载图片
        fetch(apiUrl)
            .then(res => res.json())
            .then(data => {
                // 清空加载中
                imageContainer.innerHTML = '';

                if (data.results && data.results.length > 0) {
                    // 遍历结果并显示图片
                    for (let i = 0; i < Math.min(8, data.results.length); i++) {
                        const result = data.results[i];
                        // 获取该glyph的所有图片
                        fetch(`/images/${result.id}`)
                            .then(res => res.json())
                            .then(imageData => {
                                if (imageData.image_urls && imageData.image_urls.length > 0) {
                                    const imgContainer = document.createElement('div');
                                    imgContainer.style.border = '1px solid #ddd';
                                    imgContainer.style.padding = '5px';
                                    imgContainer.style.borderRadius = '4px';
                                    imgContainer.style.textAlign = 'center';

                                    const img = document.createElement('img');
                                    img.src = imageData.image_urls[0];
                                    img.alt = `${charInfo.han} ${result.author || '未知书法家'} ${result.book_title || '未知典籍'}`;
                                    img.className = 'glyph-img'; // 添加glyph-img类名
                                    img.style.width = '100px';
                                    img.style.height = '100px';
                                    img.style.objectFit = 'contain';
                                    img.style.cursor = 'pointer';
                                    img.onclick = function () {
                                        // 更新原图片
                                        imgElement.src = imageData.image_urls[0];
                                        modal.remove();
                                    };

                                    const infoDiv = document.createElement('div');
                                    infoDiv.style.marginTop = '5px';
                                    infoDiv.style.fontSize = '12px';
                                    infoDiv.innerHTML = `<p>${result.author || '未知书法家'}</p><p>${result.book_title || '未知典籍'}</p>`;

                                    imgContainer.appendChild(img);
                                    imgContainer.appendChild(infoDiv);
                                    imageContainer.appendChild(imgContainer);
                                }
                            });
                    }
                } else {
                    // 如果没有图片，显示提示
                    const noImage = document.createElement('div');
                    noImage.textContent = '没有找到符合条件的书法图片';
                    noImage.style.width = '100%';
                    noImage.style.textAlign = 'center';
                    noImage.style.color = '#999';
                    noImage.style.padding = '20px 0';
                    imageContainer.appendChild(noImage);
                }
            })
            .catch(error => {
                console.error('加载图片失败:', error);
                imageContainer.innerHTML = '<div class="text-danger text-center p-4">加载失败，请重试</div>';
            });
    }

    // 书法家选择事件已在初始化时绑定
    // 为典籍选择添加事件监听
    $(bookSelect).on('change', function () {
        const selectedCalligrapher = $(calligrapherSelect).val() || '';
        const selectedBook = $(this).val() || '';
        console.log('典籍选择已变更(change事件):', selectedBook);
        console.log('当前书法家选择:', selectedCalligrapher);
        loadImages(selectedCalligrapher, selectedBook);
    });

    // 为典籍选择添加事件监听 (使用Select2的方式)
    $(bookSelect).on('select2:select select2:clear', function () {
        loadImages($(calligrapherSelect).val(), $(this).val());
    });

    modalBody.appendChild(imageContainer);
    modalContent.appendChild(modalBody);

    // 添加模态窗口到文档
    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // 已在Select2初始化时绑定事件，此处不再重复绑定

    // 点击模态窗口外部关闭
    modal.onclick = function (event) {
        if (event.target === modal) {
            modal.remove();
        }
    };
}
// 等待所有图片加载完成后再导出
// 保存集字结果
function saveCalligraphy() {
    const resultContainer = document.getElementById("resultContainer");
    const calligraphyResult = resultContainer.querySelector(".calligraphy-result");

    if (!calligraphyResult) {
        alert("没有可保存的集字结果");
        return;
    }

    // 这里添加保存集字结果的逻辑
    // 实际实现可能需要调用后端API保存当前的集字配置和结果
    alert("保存功能暂未实现");
}

// 导出为图片
function exportAsImage() {
    const resultContainer = document.getElementById("resultContainer");
    const calligraphyResult = resultContainer.querySelector(".calligraphy-result");

    if (!calligraphyResult) {
        alert("没有可导出的集字结果");
        return;
    }

    // 创建单个加载状态提示
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'exportLoadingIndicator';
    loadingDiv.style.position = 'fixed';
    loadingDiv.style.top = '50%';
    loadingDiv.style.left = '50%';
    loadingDiv.style.transform = 'translate(-50%, -50%)';
    loadingDiv.style.padding = '20px';
    loadingDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    loadingDiv.style.color = 'white';
    loadingDiv.style.borderRadius = '8px';
    loadingDiv.style.zIndex = '10000';
    loadingDiv.innerHTML = '<div style="text-align: center;"><div style="border: 3px solid #f3f3f3;border-top: 3px solid #3498db;border-radius: 50%;width: 30px;height: 30px;animation: spin 1s linear infinite;margin: 0 auto 10px;"></div>正在生成图片，请稍候...</div>';
    document.body.appendChild(loadingDiv);

    // 添加旋转动画
    const style = document.createElement('style');
    style.textContent = '@keyframes spin {0% { transform: rotate(0deg); }100% { transform: rotate(360deg); }}';
    document.head.appendChild(style);

    // 检查所有图片是否已加载完成
    const images = calligraphyResult.querySelectorAll('img');
    console.log('图片数量:', images.length);

    // 等待所有图片加载完成
    let loadedImages = 0;
    let allImagesLoaded = false;
    const failedImages = []; // 记录加载失败的图片
    const imageLoadTimeout = setTimeout(() => {
        console.warn('图片加载超时，继续执行导出');
        proceedWithExport();
    }, 5000); // 5秒超时

    // 如果没有图片，直接继续
    if (images.length === 0) {
        clearTimeout(imageLoadTimeout);
        proceedWithExport();
    } else {
        // 为每张图片添加加载完成事件
        images.forEach(img => {
            // 检查图片是否已经加载完成
            if (img.complete && img.naturalHeight > 0) {
                console.log('图片已加载完成:', img.src);
                loadedImages++;
                if (loadedImages === images.length) {
                    clearTimeout(imageLoadTimeout);
                    allImagesLoaded = true;
                    proceedWithExport();
                }
            } else {
                // 图片未加载完成，添加加载事件
                img.onload = function () {
                    console.log('图片加载完成:', img.src);
                    loadedImages++;
                    if (loadedImages === images.length) {
                        clearTimeout(imageLoadTimeout);
                        allImagesLoaded = true;
                        proceedWithExport();
                    }
                };

                img.onerror = function () {
                    console.error('图片加载失败:', img.src);
                    // 使用占位图替代加载失败的图片
                    img.src = window.location.origin + '/static/placeholder.png';
                    img.alt = '图片加载失败，使用占位图';
                    img.className = 'glyph-img'; // 确保占位图也有glyph-img类
                    // 记录失败的图片
                    failedImages.push(img.src);
                    loadedImages++;
                    if (loadedImages === images.length) {
                        clearTimeout(imageLoadTimeout);
                        proceedWithExport();
                    }
                };
            }
        });
    }

    function proceedWithExport() {
        // 移除加载状态 (如果存在)
        const loadingIndicator = document.getElementById('exportLoadingIndicator');
        if (loadingIndicator && loadingIndicator.parentNode === document.body) {
            document.body.removeChild(loadingIndicator);
        }

        console.log('所有图片加载状态:', allImagesLoaded ? '全部加载完成' : '部分加载或超时');
        // 如果有图片加载失败，提示用户
        if (failedImages.length > 0) {
            console.warn(`有${failedImages.length}张图片加载失败，已使用占位图替代`);
            console.warn('失败的图片URL列表:', failedImages);
            // 显示提示
            const errorDiv = document.createElement('div');
            errorDiv.style.position = 'fixed';
            errorDiv.style.top = '20px';
            errorDiv.style.left = '50%';
            errorDiv.style.transform = 'translateX(-50%)';
            errorDiv.style.padding = '10px 20px';
            errorDiv.style.backgroundColor = '#f44336';
            errorDiv.style.color = 'white';
            errorDiv.style.borderRadius = '4px';
            errorDiv.style.zIndex = '10001';
            errorDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
            errorDiv.textContent = `有${failedImages.length}张图片加载失败，已使用占位图替代`;
            document.body.appendChild(errorDiv);
            // 3秒后自动移除提示
            setTimeout(() => {
                document.body.removeChild(errorDiv);
            }, 3000);
        }

        // 收集所有图片URL和每行字数
        const images = [];
        const charContainers = document.querySelectorAll('#resultContainer .char-container, #resultContainer .missing-char');
        charContainers.forEach(container => {
            if (container.classList.contains('missing-char')) {
                // 处理缺失字符，添加占位图URL
                images.push(window.location.origin + '/static/placeholder.png');
                console.log('添加占位图URL到导出列表');
            } else {
                // 处理正常图片
                const img = container.querySelector('.glyph-img');
                if (img && img.src && img.src.trim() !== '') {
                    images.push(img.src.trim());
                }
            }
        });

        console.log('收集到的图片URL数量:', images.length);
        console.log('图片URL列表:', images);

        // 如果没有收集到图片，显示错误信息
        if (images.length === 0) {
            alert('没有找到可导出的图片，请先生成集字结果');
            return;
        }

        // 获取每行显示的字数
        const charsPerLine = parseInt(document.getElementById('charsPerLineInput').value) || 10;

        // 重新显示加载状态
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'exportLoadingIndicator';
        loadingDiv.style.position = 'fixed';
        loadingDiv.style.top = '50%';
        loadingDiv.style.left = '50%';
        loadingDiv.style.transform = 'translate(-50%, -50%)';
        loadingDiv.style.padding = '20px';
        loadingDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        loadingDiv.style.color = 'white';
        loadingDiv.style.borderRadius = '8px';
        loadingDiv.style.zIndex = '10000';
        loadingDiv.innerHTML = '<div style="text-align: center;"><div style="border: 3px solid #f3f3f3;border-top: 3px solid #3498db;border-radius: 50%;width: 30px;height: 30px;animation: spin 1s linear infinite;margin: 0 auto 10px;"></div>正在生成图片，请稍候...</div>';
        document.body.appendChild(loadingDiv);

        // 发送请求到后端API
        // 获取当前选择的排列方向
        const directionSelect = document.getElementById('directionSelect');
        const direction = directionSelect ? directionSelect.value : 'horizontal';

        // 调试信息：确认占位图是否被包含
        console.log('准备发送到后端的图片URL数量:', images.length);
        console.log('准备发送到后端的图片URL列表:', images);
        const hasPlaceholder = images.some(url => url.includes('placeholder.png'));
        console.log('发送的URL中是否包含占位图:', hasPlaceholder);

        fetch('/export_image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                images: images,
                cols: charsPerLine,
                direction: direction
            })
        })
            .then(response => {
                // 移除加载状态
                if (loadingDiv && loadingDiv.parentNode === document.body) {
                    document.body.removeChild(loadingDiv);
                }

                if (!response.ok) {
                    throw new Error('导出图片失败');
                }
                return response.blob();
            })
            .then(blob => {
                // 移除加载状态
                const loadingIndicator = document.getElementById('exportLoadingIndicator');
                if (loadingIndicator && loadingIndicator.parentNode === document.body) {
                    document.body.removeChild(loadingIndicator);
                }

                // 创建下载链接
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'calligraphy_set.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                // 显示下载完成提示
                const successDiv = document.createElement('div');
                successDiv.style.position = 'fixed';
                successDiv.style.top = '20px';
                successDiv.style.left = '50%';
                successDiv.style.transform = 'translateX(-50%)';
                successDiv.style.padding = '10px 20px';
                successDiv.style.backgroundColor = '#4CAF50';
                successDiv.style.color = 'white';
                successDiv.style.borderRadius = '4px';
                successDiv.style.zIndex = '10001';
                successDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
                successDiv.innerHTML = '<div style="display: flex; align-items: center;"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;"><polyline points="20 6 9 17 4 12"></polyline></svg>图片已成功导出并下载</div>';
                document.body.appendChild(successDiv);

                // 5秒后自动移除提示
                setTimeout(() => {
                    document.body.removeChild(successDiv);
                }, 5000);

                // 提供可选的预览按钮
                const previewBtn = document.createElement('button');
                previewBtn.style.position = 'fixed';
                previewBtn.style.bottom = '20px';
                previewBtn.style.right = '20px';
                previewBtn.style.padding = '10px 15px';
                previewBtn.style.backgroundColor = '#2196F3';
                previewBtn.style.color = 'white';
                previewBtn.style.border = 'none';
                previewBtn.style.borderRadius = '4px';
                previewBtn.style.cursor = 'pointer';
                previewBtn.style.zIndex = '10001';
                previewBtn.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
                previewBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; vertical-align: middle;"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><circle cx="12" cy="12" r="3"></circle><line x1="16.24" y1="7.76" x2="14.12" y2="9.88"></line><line x1="8" y1="12" x2="12" y2="12"></line><line x1="9.88" y1="14.12" x2="7.76" y2="16.24"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>查看预览';
                document.body.appendChild(previewBtn);

                previewBtn.onclick = function () {
                    const previewWindow = window.open('', '_blank');
                    if (previewWindow) {
                        const img = new Image();
                        img.src = url;
                        previewWindow.document.write('<html><head><title>导出预览</title></head><body style="margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh;"><img src="' + url + '" style="max-width: 90%; max-height: 90%;" /></body></html>');
                        document.body.removeChild(previewBtn);
                    } else {
                        console.warn('预览窗口被浏览器阻止');
                        alert('预览窗口被浏览器阻止，请允许弹出窗口后重试');
                    }
                };

                // 10秒后自动移除预览按钮
                setTimeout(() => {
                    if (previewBtn && previewBtn.parentNode === document.body) {
                        document.body.removeChild(previewBtn);
                    }
                }, 10000);
            })
            .catch(error => {
                // 移除加载状态
                const loadingIndicator = document.getElementById('exportLoadingIndicator');
                if (loadingIndicator && loadingIndicator.parentNode === document.body) {
                    document.body.removeChild(loadingIndicator);
                }

                console.error('导出图片失败:', error);
                alert('导出图片失败，请重试');
            });
    }
}
