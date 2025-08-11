document.addEventListener("DOMContentLoaded", () => {
    // 加载选项（字体、书法家、典籍）
    loadOptions();

    // 添加事件监听器
    document.getElementById("generateBtn").addEventListener("click", generateCalligraphy);
    document.getElementById("clearBtn").addEventListener("click", clearContent);
    document.getElementById("saveBtn").addEventListener("click", saveCalligraphy);
    document.getElementById("exportBtn").addEventListener("click", exportAsImage);
    
    // 添加输入框过滤功能
    const textInput = document.getElementById("textInput");
    textInput.addEventListener("input", filterTextInput);
    textInput.addEventListener("paste", handlePaste);
    
    // 添加窗口大小变化监听器
    let resizeTimeout;
    window.addEventListener("resize", () => {
        // 防抖处理，避免频繁调整
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            adjustCharContainerSizes();
        }, 300);
    });
    

});

// 过滤输入文本，去除标点符号和英文字母
function filterTextInput(event) {
    const input = event.target;
    const cursorPosition = input.selectionStart;
    const originalValue = input.value;
    
    // 过滤掉标点符号和英文字母，只保留中文字符、数字和空格
    const filteredValue = originalValue.replace(/[^\u4e00-\u9fa5\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\uf900-\ufaff\u3300-\u33ff\ufe30-\ufe4f\uf900-\ufaff\u2f800-\u2fa1f0-9\s]/g, '');
    
    if (filteredValue !== originalValue) {
        input.value = filteredValue;
        
        // 计算新的光标位置
        const removedChars = originalValue.length - filteredValue.length;
        const newCursorPosition = Math.max(0, cursorPosition - removedChars);
        
        // 恢复光标位置
        input.setSelectionRange(newCursorPosition, newCursorPosition);
        
        // 显示提示信息
        showFilterNotification();
    }
}

// 处理粘贴事件
function handlePaste(event) {
    event.preventDefault();
    
    // 获取粘贴的文本
    const pastedText = (event.clipboardData || window.clipboardData).getData('text');
    
    // 过滤文本
    const filteredText = pastedText.replace(/[^\u4e00-\u9fa5\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\uf900-\ufaff\u3300-\u33ff\ufe30-\ufe4f\uf900-\ufaff\u2f800-\u2fa1f0-9\s]/g, '');
    
    // 获取当前光标位置
    const input = event.target;
    const cursorPosition = input.selectionStart;
    const currentValue = input.value;
    
    // 插入过滤后的文本
    const newValue = currentValue.slice(0, cursorPosition) + filteredText + currentValue.slice(input.selectionEnd);
    input.value = newValue;
    
    // 设置新的光标位置
    const newCursorPosition = cursorPosition + filteredText.length;
    input.setSelectionRange(newCursorPosition, newCursorPosition);
    
    // 如果过滤掉了字符，显示提示
    if (filteredText !== pastedText) {
        showFilterNotification();
    }
}

// 显示过滤提示
function showFilterNotification() {
    // 避免重复显示提示
    if (document.getElementById('filter-notification')) {
        return;
    }
    
    const notification = document.createElement('div');
    notification.id = 'filter-notification';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '10px 15px';
    notification.style.backgroundColor = '#ffc107';
    notification.style.color = '#856404';
    notification.style.borderRadius = '4px';
    notification.style.zIndex = '10001';
    notification.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    notification.style.fontSize = '14px';
    notification.innerHTML = '<div style="display: flex; align-items: center;"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>已自动过滤标点符号和英文字母</div>';
    
    document.body.appendChild(notification);
    
    // 2秒后自动移除提示
    setTimeout(() => {
        if (notification && notification.parentNode) {
            document.body.removeChild(notification);
        }
    }, 2000);
}

// 显示字数提示
function showCharCountNotification(charCount) {
    // 避免重复显示提示
    if (document.getElementById('char-count-notification')) {
        return;
    }
    
    const notification = document.createElement('div');
    notification.id = 'char-count-notification';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '12px 16px';
    notification.style.backgroundColor = '#17a2b8';
    notification.style.color = 'white';
    notification.style.borderRadius = '6px';
    notification.style.zIndex = '10001';
    notification.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    notification.style.fontSize = '14px';
    notification.style.maxWidth = '300px';
    notification.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 4px;">字数较多提醒</div>
        <div style="font-size: 13px;">您输入了 ${charCount} 个字符，生成后可滚动查看完整结果</div>
    `;
    
    document.body.appendChild(notification);
    
    // 4秒后自动移除提示
    setTimeout(() => {
        if (notification && notification.parentNode) {
            document.body.removeChild(notification);
        }
    }, 4000);
}

// 加载选项（字体、书法家、典籍）
function loadOptions() {
    fetch("/api/options")
        .then(res => res.json())
        .then(data => {
            // 加载字体选项
            const fontSelect = document.getElementById("fontSelect");
            fontSelect.innerHTML = '<option value="">字体</option>';
            data.fonts.forEach(font => {
                const option = document.createElement("option");
                option.value = font;
                option.textContent = font;
                fontSelect.appendChild(option);
            });
            $(fontSelect).select2({
                placeholder: '字体',
                allowClear: true,
                width: '100%'
            }).on('select2:open select2:close', function() {
                // 强制重新应用高度样式
                setTimeout(() => {
                    $('.select2-container').css('height', '44px');
                    $('.select2-selection').css('height', '44px');
                }, 10);
            });

            // 加载书法家选项
            const calligrapherSelect = document.getElementById("calligrapherSelect");
            calligrapherSelect.innerHTML = '<option value="">书法家</option>';
            data.authors.forEach(author => {
                const option = document.createElement("option");
                option.value = author;
                option.textContent = author;
                calligrapherSelect.appendChild(option);
            });
            $(calligrapherSelect).select2({
                placeholder: '书法家',
                allowClear: true,
                width: '100%'
            }).on('select2:open select2:close', function() {
                // 强制重新应用高度样式
                setTimeout(() => {
                    $('.select2-container').css('height', '44px');
                    $('.select2-selection').css('height', '44px');
                }, 10);
            });

            // 加载典籍选项
            const bookSelect = document.getElementById("bookSelect");
            bookSelect.innerHTML = '<option value="">典籍</option>';
            data.books.forEach(book => {
                const option = document.createElement("option");
                option.value = book;
                option.textContent = book;
                bookSelect.appendChild(option);
            });
            $(bookSelect).select2({
                placeholder: '典籍',
                allowClear: true,
                width: '100%'
            }).on('select2:open select2:close', function() {
                // 强制重新应用高度样式
                setTimeout(() => {
                    $('.select2-container').css('height', '44px');
                    $('.select2-selection').css('height', '44px');
                }, 10);
            });

            // 初始化排列方式选择框
            const directionSelect = document.getElementById("directionSelect");
            $(directionSelect).select2({
                placeholder: '排列方式',
                allowClear: true,
                width: '100%'
            }).on('select2:open select2:close', function() {
                // 强制重新应用高度样式
                setTimeout(() => {
                    $('.select2-container').css('height', '44px');
                    $('.select2-selection').css('height', '44px');
                }, 10);
            });
            
            // 设置默认选中值
            $(directionSelect).val('horizontal').trigger('change');

            // 所有Select2初始化完成后，统一强制应用高度样式
            setTimeout(() => {
                $('.select2-container').css('height', '44px');
                $('.select2-selection').css('height', '44px');
                $('.select2-selection__rendered').css('line-height', '40px');
            }, 100);
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

    // 字数检查和提醒
    const charCount = textInput.length;
    if (charCount > 100) {
        const confirmed = confirm(
            `您输入了 ${charCount} 个字符，内容较多可能需要滚动查看。\n\n` +
            `建议：\n` +
            `• 字数较多时建议分段处理\n` +
            `• 可以调整"每行字数"来优化布局\n` +
            `• 生成后可以滚动查看完整结果\n\n` +
            `是否继续生成集字？`
        );
        if (!confirmed) {
            return;
        }
    } else if (charCount > 50) {
        // 50-100字给出温和提示
        showCharCountNotification(charCount);
    }

    const resultContainer = document.getElementById("resultContainer");
    resultContainer.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <div class="generate-spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 40px; height: 40px; margin: 0 auto; animation: generate-spin 1s linear infinite;"></div>
            <div style="margin-top: 10px; color: #007bff;">正在生成集字...</div>
        </div>
    `;
    
    // 确保生成集字的spinner动画样式存在
    if (!document.getElementById('generate-spinner-style')) {
        const style = document.createElement('style');
        style.id = 'generate-spinner-style';
        style.textContent = '@keyframes generate-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
        document.head.appendChild(style);
    }

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

// 获取响应式字符容器尺寸
function getResponsiveCharSize() {
    const screenWidth = window.innerWidth;
    if (screenWidth <= 576) {
        // 窄屏：更小的尺寸
        return { width: "60px", margin: "0" };
    } else if (screenWidth <= 768) {
        // 中等屏幕：中等尺寸
        return { width: "80px", margin: "0" };
    } else {
        // 大屏幕：较大尺寸
        return { width: "100px", margin: "0" };
    }
}

// 调整现有字符容器的尺寸
function adjustCharContainerSizes() {
    const charSize = getResponsiveCharSize();
    const containers = document.querySelectorAll('#resultContainer .char-container, #resultContainer .missing-char');
    
    containers.forEach(container => {
        container.style.width = charSize.width;
        container.style.margin = "0";
        // 确保aspect-ratio生效
        container.style.aspectRatio = "1/1";
    });
}

// 渲染集字结果
function renderCalligraphyResult(characters, direction) {
    const resultContainer = document.getElementById("resultContainer");
    resultContainer.innerHTML = '';

    // 计算统计信息并更新标题行的统计区域
    const actualChars = characters.filter(char => !char.placeholder);
    const totalChars = actualChars.length;
    const foundChars = actualChars.filter(char => char.image_urls && char.image_urls.length > 0).length;
    const missingChars = totalChars - foundChars;
    
    const statsDiv = document.getElementById("calligraphyStats");
    statsDiv.innerHTML = `共 ${totalChars} 字 | 找到 ${foundChars} 字 | 缺失 ${missingChars} 字`;

    const resultDiv = document.createElement("div");
    resultDiv.className = "calligraphy-result";
    resultDiv.style.padding = "16px";

    // 获取每行显示字数
    const charsPerLine = parseInt(document.getElementById("charsPerLineInput").value) || 5;
    
    // 根据排列方向设置不同的布局方案
    if (direction === 'vertical-left' || direction === 'vertical-right') {
        // 垂直布局：使用CSS Grid列优先排列
        const numCols = Math.ceil(characters.length / charsPerLine);
        
        // 为所有垂直排列方式添加占位符补齐
        const totalSlots = numCols * charsPerLine;
        const paddedCharacters = [...characters];
        
        // 添加占位符直到填满所有位置
        while (paddedCharacters.length < totalSlots) {
            paddedCharacters.push({
                han: '',
                image_urls: null,
                placeholder: true
            });
        }
        
        // 对于vertical-right，需要重新排列字符顺序
        if (direction === 'vertical-right') {
            const rearrangedCharacters = [];
            // 右起排列：最右边的列先填满（从上到下），再填充左边的列
            let charIndex = 0;
            for (let col = numCols - 1; col >= 0; col--) {
                for (let row = 0; row < charsPerLine; row++) {
                    // 计算在Grid中的位置（从左到右的列索引）
                    const gridPosition = col * charsPerLine + row;
                    rearrangedCharacters[gridPosition] = paddedCharacters[charIndex];
                    charIndex++;
                }
            }
            characters = rearrangedCharacters;
        } else {
            // vertical-left 直接使用补齐后的字符数组
            characters = paddedCharacters;
        }
        
        resultDiv.style.display = "grid";
        resultDiv.style.gridTemplateColumns = `repeat(${numCols}, auto)`;
        resultDiv.style.gridTemplateRows = `repeat(${charsPerLine}, auto)`;
        resultDiv.style.gridAutoFlow = "column";
        resultDiv.style.gap = "0px";
        resultDiv.style.width = "100%";
        resultDiv.style.minWidth = "100%";
        // 对齐：左起/右起
        if (direction === 'vertical-right') {
            resultDiv.style.setProperty('justify-content', 'flex-end', 'important');
        } else {
            resultDiv.style.setProperty('justify-content', 'flex-start', 'important');
        }
        resultDiv.style.alignItems = "flex-start";
    } else {
        // 水平布局：使用CSS Grid精确控制每行字符数
        resultDiv.style.display = "grid";
        resultDiv.style.gridTemplateColumns = `repeat(${charsPerLine}, auto)`;
        resultDiv.style.gap = "0px";
        resultDiv.style.justifyContent = "start";
        resultDiv.style.width = "max-content"; // 允许内容超出容器宽度
        
        // 计算内容的实际宽度，确保能够触发横向滚动
        const charSize = getResponsiveCharSize();
        const contentWidth = charsPerLine * parseInt(charSize.width);
        const containerWidth = resultContainer.clientWidth || 800; // 获取容器宽度，默认800px
        
        if (contentWidth > containerWidth) {
            resultDiv.style.minWidth = `${contentWidth}px`; // 设置为内容实际宽度
        } else {
            resultDiv.style.minWidth = "100%"; // 确保至少占满容器宽度
        }
        
        resultDiv.style.overflowX = "visible"; // 确保内容可以超出
        
        if (direction === 'horizontal') {
            // 从左到右：正常顺序
            resultDiv.style.gridAutoFlow = "row";
        } else if (direction === 'horizontal-reverse') {
            // 从右到左：需要特殊处理
            resultDiv.style.gridAutoFlow = "row";
            resultDiv.style.direction = "rtl"; // 使用RTL布局实现从右到左
            resultDiv.style.justifyContent = "end";
        }
        resultDiv.style.alignItems = "start";

        // 在水平排列下，使用占位符补齐到整行个数
        const totalSlots = Math.ceil(characters.length / charsPerLine) * charsPerLine;
        const paddedCharacters = [...characters];
        while (paddedCharacters.length < totalSlots) {
            paddedCharacters.push({ han: '', image_urls: null, placeholder: true });
        }
        characters = paddedCharacters;
    }

    // 获取当前屏幕的响应式尺寸
    const charSize = getResponsiveCharSize();
    
    characters.forEach(charInfo => {
        const charContainer = document.createElement("div");
        
        if (charInfo.placeholder) {
            // 占位符：使用placeholder.png图片填充
            charContainer.className = "char-container placeholder-grid";
            charContainer.style.display = "block";
            charContainer.style.margin = "0";
            charContainer.style.position = "relative";
            charContainer.style.width = charSize.width;
            charContainer.style.aspectRatio = "1/1";
            charContainer.style.flexShrink = "0";
            charContainer.style.boxSizing = "border-box";
            charContainer.style.padding = "0";
            charContainer.style.overflow = "hidden";
            charContainer.style.border = "none";
            charContainer.style.pointerEvents = "none";
            // 确保RTL布局下字符内容正常显示
            if (direction === 'horizontal-reverse') {
                charContainer.style.direction = "ltr";
            }

            // 创建占位图片元素
            const placeholderImg = document.createElement("img");
            placeholderImg.src = window.location.origin + '/static/placeholder.png';
            placeholderImg.alt = "占位符";
            placeholderImg.className = 'placeholder-img';
            placeholderImg.style.width = '100%';
            placeholderImg.style.height = '100%';
            placeholderImg.style.objectFit = 'contain';
            placeholderImg.style.pointerEvents = 'none';
            
            charContainer.appendChild(placeholderImg);
        } else if (charInfo.image_urls && charInfo.image_urls.length > 0) {
            // 有图片的字符
            charContainer.className = "char-container glyph-card";
            charContainer.style.display = "block";
            charContainer.style.margin = "0";
            charContainer.style.position = "relative";
            charContainer.style.width = charSize.width;
            charContainer.style.aspectRatio = "1/1";
            charContainer.style.flexShrink = "0";
            charContainer.style.boxSizing = "border-box";
            charContainer.style.padding = "0";
            charContainer.style.overflow = "hidden";
            // 确保RTL布局下字符内容正常显示
            if (direction === 'horizontal-reverse') {
                charContainer.style.direction = "ltr";
            }

            // 添加图片ID数据属性
            if (charInfo.image_ids && charInfo.image_ids.length > 0) {
                charContainer.setAttribute('data-image-id', charInfo.image_ids[0]);
            }

            // 创建图片元素
            const img = document.createElement("img");
            img.src = charInfo.image_urls[0];
            img.alt = charInfo.han;
            img.className = 'glyph-img';
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'contain';
            img.style.cursor = 'pointer';
            
            // 添加点击事件用于替换图片
            img.onclick = function() {
                openCharSelectionModal(charInfo, img);
            };

            charContainer.appendChild(img);
        } else {
            // 缺失字符，显示字符本身并支持点击选择
            charContainer.className = "char-container missing-char";
            charContainer.style.display = "block";
            charContainer.style.margin = "0";
            charContainer.style.position = "relative";
            charContainer.style.width = charSize.width;
            charContainer.style.aspectRatio = "1/1";
            charContainer.style.flexShrink = "0";
            charContainer.style.boxSizing = "border-box";
            charContainer.style.padding = "0";
            charContainer.style.overflow = "hidden";
            charContainer.style.backgroundColor = "#f8f8f8";
            charContainer.style.border = "1px solid #ddd";
            charContainer.style.display = "flex";
            charContainer.style.alignItems = "center";
            charContainer.style.justifyContent = "center";
            charContainer.style.fontSize = "24px";
            charContainer.style.fontWeight = "bold";
            charContainer.style.color = "#333";
            charContainer.style.cursor = "pointer";
            // 确保RTL布局下字符内容正常显示
            if (direction === 'horizontal-reverse') {
                charContainer.style.direction = "ltr";
            }
            charContainer.textContent = charInfo.han;
            
            // 添加点击事件用于选择字符
            charContainer.onclick = function() {
                openCharSelectionModal(charInfo, charContainer);
            };
        }

        resultDiv.appendChild(charContainer);
    });

    resultContainer.appendChild(resultDiv);
    
    // 添加滚动提示信息（在容器外部）
    if (totalChars > 20) {
        const scrollHintDiv = document.createElement("div");
        scrollHintDiv.className = "scroll-hint-container";
        scrollHintDiv.style.cssText = `
            text-align: center;
            padding: 8px 16px;
            margin-top: 8px;
            font-size: 12px;
            color: #adb5bd;
            background-color: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        `;
        
        let scrollHint = '';
        if (direction === 'vertical-left' || direction === 'vertical-right') {
            scrollHint = '内容较多，可上下滚动查看 ↕';
        } else {
            scrollHint = '内容较多，可上下左右滚动查看 ↕↔';
        }
        
        scrollHintDiv.textContent = scrollHint;
        resultContainer.appendChild(scrollHintDiv);
    }
    
    // 如果字数较多，添加回到顶部按钮
    if (totalChars > 30) {
        addScrollToTopButton(resultContainer);
    }
}

// 添加回到顶部按钮
function addScrollToTopButton(container) {
    // 移除现有的回到顶部按钮（如果有）
    const existingButton = document.getElementById('scroll-to-top-btn');
    if (existingButton) {
        existingButton.remove();
    }
    
    const scrollButton = document.createElement('button');
    scrollButton.id = 'scroll-to-top-btn';
    scrollButton.innerHTML = '↑';
    scrollButton.style.cssText = `
        position: absolute;
        bottom: 16px;
        right: 16px;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #007bff;
        color: white;
        border: none;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        z-index: 100;
        opacity: 0;
        transition: opacity 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    // 点击回到顶部
    scrollButton.onclick = function() {
        container.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    };
    
    container.appendChild(scrollButton);
    
    // 监听滚动事件，控制按钮显示/隐藏
    container.addEventListener('scroll', function() {
        if (container.scrollTop > 200) {
            scrollButton.style.opacity = '1';
        } else {
            scrollButton.style.opacity = '0';
        }
    });
}

// 清空内容
function clearContent() {
    document.getElementById("textInput").value = '';
    document.getElementById("resultContainer").innerHTML = '<p class="text-muted">请输入文字并点击生成按钮</p>';
    document.getElementById("calligraphyStats").innerHTML = '';
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
    margin: 5% auto;
    padding: 15px 0px;
    border: 1px solid #888;
    width: 95%;
    max-width: 800px;
    min-width: 320px;
    max-height: 85vh;
    border-radius: 8px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
    box-sizing: border-box;
}

@media (min-width: 768px) {
    .modal-content {
        width: 85%;
        margin: 8% auto;
        padding: 20px 0px;
    }
}

@media (min-width: 1024px) {
    .modal-content {
        width: 75%;
        margin: 10% auto;
    }
}

.modal-content::-webkit-scrollbar {
    width: 12px;
}

.modal-content::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
}

.modal-content::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 6px;
    border: 1px solid #666;
}

.modal-content::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* 为Firefox添加滚动条样式 */
.modal-content {
    scrollbar-width: auto;
    scrollbar-color: #888 #f1f1f1;
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

    // 模态标题
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    modalHeader.style.display = 'flex';
    modalHeader.style.justifyContent = 'space-between';
    modalHeader.style.alignItems = 'center';
    modalHeader.style.marginBottom = '15px';
    modalHeader.style.marginLeft = '15px';
    modalHeader.style.marginRight = '15px';

    const modalTitle = document.createElement('h5');
    modalTitle.className = 'modal-title';
    modalTitle.textContent = `替换集字`;
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
    modalBody.style.padding = '0px';
    modalBody.style.margin = '0px';

    // 创建选择器容器（响应式布局）
    const selectorsContainer = document.createElement('div');
    selectorsContainer.style.display = 'flex';
    selectorsContainer.style.gap = '10px';
    selectorsContainer.style.marginBottom = '15px';
    selectorsContainer.style.marginLeft = '15px';
    selectorsContainer.style.marginRight = '15px';
    selectorsContainer.style.flexWrap = 'wrap';
    
    // 在小屏幕上垂直排列
    if (window.innerWidth < 480) {
        selectorsContainer.style.flexDirection = 'column';
    }

    // 书法家选择框容器
    const calligrapherDiv = document.createElement('div');
    calligrapherDiv.style.flex = '1';

    const calligrapherSelect = document.createElement('select');
    calligrapherSelect.id = 'modalCalligrapherSelect';
    calligrapherSelect.className = 'form-control';
    calligrapherSelect.innerHTML = '<option value="">选择书法家</option>';

    calligrapherDiv.appendChild(calligrapherSelect);

    // 典籍选择框容器
    const bookDiv = document.createElement('div');
    bookDiv.style.flex = '1';

    const bookSelect = document.createElement('select');
    bookSelect.id = 'modalBookSelect';
    bookSelect.className = 'form-control';
    bookSelect.innerHTML = '<option value="">选择典籍</option>';

    bookDiv.appendChild(bookSelect);

    // 将两个选择框添加到容器中
    selectorsContainer.appendChild(calligrapherDiv);
    selectorsContainer.appendChild(bookDiv);
    modalBody.appendChild(selectorsContainer);

    // 图片展示区域
    const imageContainer = document.createElement('div');
    imageContainer.id = 'imageContainer';
    imageContainer.style.display = 'grid';
    imageContainer.style.gap = '20px';
    imageContainer.style.marginTop = '15px';
    imageContainer.style.padding = '0px';
    imageContainer.style.justifyItems = 'center';
    imageContainer.style.width = '100%';
    imageContainer.style.maxWidth = '100%';
    imageContainer.style.boxSizing = 'border-box';
    imageContainer.style.overflowX = 'hidden';
    
    // 分页相关变量 - 需要在updateGridLayout函数之前定义
    let currentPage = 0;
    let pageSize = window.innerWidth >= 680 ? 16 : (window.innerWidth >= 500 ? 12 : 8);
    let allResults = [];
    let isLoading = false;
    let hasMoreData = true;
    
    // 响应式网格布局 - 基于屏幕宽度
    function updateGridLayout() {
        const screenWidth = window.innerWidth;
        if (screenWidth >= 680) {
            // 大屏幕：4列
            imageContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
            pageSize = 16; // 4列 × 4行 = 16个
        } else if (screenWidth >= 500) {
            // 中等屏幕：3列
            imageContainer.style.gridTemplateColumns = 'repeat(3, 1fr)';
            pageSize = 12; // 3列 × 4行 = 12个
        } else if (screenWidth >= 350) {
            // 小屏幕：2列
            imageContainer.style.gridTemplateColumns = 'repeat(2, 1fr)';
            pageSize = 8; // 2列 × 4行 = 8个
        } else {
            // 超小屏幕：1列
            imageContainer.style.gridTemplateColumns = '1fr';
            pageSize = 6; // 1列 × 6行 = 6个
        }
        console.log(`屏幕宽度: ${screenWidth}px, 每页显示: ${pageSize}个图片`);
    }
    
    // 初始设置网格布局
    updateGridLayout();
    
    // 监听窗口大小变化
    window.addEventListener('resize', updateGridLayout);

    // 滚动提示
    const scrollHint = document.createElement('div');
    scrollHint.id = 'scrollHint';
    scrollHint.innerHTML = '↓ 向下滚动查看更多图片 ↓';
    scrollHint.style.textAlign = 'center';
    scrollHint.style.color = '#666';
    scrollHint.style.fontSize = '14px';
    scrollHint.style.padding = '10px';
    scrollHint.style.marginTop = '10px';
    scrollHint.style.display = 'none'; // 初始隐藏

    // 确保模态窗口已添加到文档
    console.log('模态窗口创建中...');

    // 从数据库加载该字符的书法家和典籍选项
    console.log('开始加载字符选项...', charInfo.han);
    fetch(`/api/char_options?han=${encodeURIComponent(charInfo.han)}`)
        .then(res => {
            console.log('api/char_options响应状态:', res.status);
            if (!res.ok) {
                throw new Error(`HTTP错误! 状态码: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log('成功获取字符选项数据:', data);
            // 加载书法家选项
            if (data.authors && Array.isArray(data.authors)) {
                console.log(`字符 "${charInfo.han}" 的书法家选项数量:`, data.authors.length);
                data.authors.forEach(author => {
                    const option = document.createElement('option');
                    option.value = author;
                    option.textContent = author;
                    calligrapherSelect.appendChild(option);
                });
            } else {
                console.log('该字符没有可用的书法家选项');
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
                console.log(`字符 "${charInfo.han}" 的典籍选项数量:`, data.books.length);
                data.books.forEach(book => {
                    const option = document.createElement('option');
                    option.value = book;
                    option.textContent = book;
                    bookSelect.appendChild(option);
                });
            } else {
                console.log('该字符没有可用的典籍选项');
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



    // 创建图片卡片的函数
    function createImageCard(result, imageData) {
        const modalImageCard = document.createElement('div');
        modalImageCard.style.border = '1px solid #ddd';
        modalImageCard.style.padding = '0px';
        modalImageCard.style.margin = '0px 0px auto 0px'; // 上0 右0 下auto 左0
        modalImageCard.style.borderRadius = '6px';
        modalImageCard.style.textAlign = 'center';
        modalImageCard.style.display = 'flex';
        modalImageCard.style.flexDirection = 'column';
        modalImageCard.style.alignItems = 'center';
        modalImageCard.style.width = 'auto';
        modalImageCard.style.maxWidth = '160px';
        modalImageCard.style.minWidth = '120px';
        modalImageCard.style.backgroundColor = '#fafafa';
        modalImageCard.style.transition = 'all 0.2s ease';
        modalImageCard.style.cursor = 'pointer';
        
        // 添加悬停效果
        modalImageCard.onmouseenter = function() {
            this.style.backgroundColor = '#f0f0f0';
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        };
        modalImageCard.onmouseleave = function() {
            this.style.backgroundColor = '#fafafa';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
        };

        const img = document.createElement('img');
        img.src = imageData.image_urls[0];
        img.alt = `${charInfo.han} ${result.author || '未知书法家'} ${result.book_title || '未知典籍'}`;
        img.className = 'modal-glyph-img';
        img.style.width = '100%';
        img.style.height = '120px';
        img.style.objectFit = 'contain';
        img.style.setProperty('border-radius', '5px 5px 0 0', 'important');
        img.style.display = 'block';
        
        // 将点击事件添加到整个容器
        modalImageCard.onclick = function () {
            // 检查原元素是否是缺失字符容器
            if (imgElement.tagName === 'DIV' && imgElement.classList.contains('missing-char')) {
                // 替换缺失字符容器为图片
                const newImg = document.createElement('img');
                newImg.src = imageData.image_urls[0];
                newImg.alt = charInfo.han;
                newImg.className = 'glyph-img';
                newImg.style.width = '100%';
                newImg.style.height = '100%';
                newImg.style.objectFit = 'contain';
                newImg.style.cursor = 'pointer';
                
                // 添加点击事件用于替换图片
                newImg.onclick = function() {
                    openCharSelectionModal(charInfo, newImg);
                };
                
                // 更新容器样式为图片容器
                imgElement.className = "char-container glyph-card";
                imgElement.style.backgroundColor = "transparent";
                imgElement.style.border = "none";
                imgElement.style.fontSize = "";
                imgElement.style.fontWeight = "";
                imgElement.style.color = "";
                imgElement.textContent = "";
                imgElement.onclick = null;
                
                // 添加图片ID数据属性
                if (imageData.image_ids && imageData.image_ids.length > 0) {
                    imgElement.setAttribute('data-image-id', imageData.image_ids[0]);
                }
                
                // 添加图片到容器
                imgElement.appendChild(newImg);
            } else {
                // 更新原图片
                imgElement.src = imageData.image_urls[0];
                // 更新父容器的图片ID
                const container = imgElement.closest('.char-container');
                if (container && imageData.image_ids && imageData.image_ids.length > 0) {
                    container.setAttribute('data-image-id', imageData.image_ids[0]);
                }
            }
            modal.remove();
        };

        const infoDiv = document.createElement('div');
        infoDiv.style.marginTop = '0px';
        infoDiv.style.fontSize = '12px';
        infoDiv.style.color = '#666';
        infoDiv.style.lineHeight = '1.2';
        infoDiv.style.whiteSpace = 'nowrap';
        infoDiv.style.overflow = 'hidden';
        infoDiv.style.textOverflow = 'ellipsis';
        infoDiv.style.width = 'auto';
        infoDiv.style.maxWidth = '120px';
        infoDiv.style.margin = '0';
        infoDiv.style.padding = '2px 2px 4px 2px';
        infoDiv.style.boxSizing = 'border-box';
        infoDiv.innerHTML = `${result.author || '未知书法家'} | ${result.book_title || '未知典籍'}`;

        modalImageCard.appendChild(img);
        modalImageCard.appendChild(infoDiv);
        return modalImageCard;
    }

    // 加载更多图片的函数
    function loadMoreImages() {
        if (isLoading || !hasMoreData) return;
        
        isLoading = true;
        
        // 显示加载中指示器
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loadingIndicator';
        loadingIndicator.style.textAlign = 'center';
        loadingIndicator.style.padding = '20px';
        loadingIndicator.style.width = '100%';
        loadingIndicator.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                <div class="modal-spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 20px; height: 20px; animation: modal-spin 1s linear infinite;"></div>
                <div style="color: #666; font-size: 12px;">加载更多...</div>
            </div>
        `;
        imageContainer.appendChild(loadingIndicator);

        // 计算当前页要显示的数据
        const startIndex = currentPage * pageSize;
        const endIndex = Math.min(startIndex + pageSize, allResults.length);
        
        console.log(`加载第${currentPage + 1}页，索引${startIndex}-${endIndex - 1}`);

        // 加载当前页的图片
        const promises = [];
        for (let i = startIndex; i < endIndex; i++) {
            const result = allResults[i];
            const promise = fetch(`/images/${result.id}`)
                .then(res => res.json())
                .then(imageData => {
                    if (imageData.image_urls && imageData.image_urls.length > 0) {
                        return { result, imageData };
                    }
                    return null;
                })
                .catch(error => {
                    console.error('加载图片失败:', error);
                    return null;
                });
            promises.push(promise);
        }

        Promise.all(promises).then(results => {
            // 移除加载指示器
            const indicator = document.getElementById('loadingIndicator');
            if (indicator) {
                indicator.remove();
            }

            // 添加新的图片卡片 - 为每张图片创建单独的卡片
            results.forEach(item => {
                if (item && item.imageData.image_urls) {
                    // 为每张图片创建一个卡片
                    item.imageData.image_urls.forEach((imageUrl, imageIndex) => {
                        // 创建单张图片的数据
                        const singleImageData = {
                            image_urls: [imageUrl],
                            image_ids: item.imageData.image_ids ? [item.imageData.image_ids[imageIndex]] : []
                        };
                        const card = createImageCard(item.result, singleImageData);
                        imageContainer.appendChild(card);
                    });
                }
            });

            currentPage++;
            isLoading = false;
            
            // 检查是否还有更多数据
            if (currentPage * pageSize >= allResults.length) {
                hasMoreData = false;
                // 隐藏滚动提示
                const scrollHint = document.getElementById('scrollHint');
                if (scrollHint) {
                    scrollHint.style.display = 'none';
                }
                // 添加"没有更多了"提示
                if (allResults.length > pageSize) {
                    const noMoreDiv = document.createElement('div');
                    noMoreDiv.style.textAlign = 'center';
                    noMoreDiv.style.padding = '20px';
                    noMoreDiv.style.width = '100%';
                    noMoreDiv.style.color = '#999';
                    noMoreDiv.style.fontSize = '12px';
                    noMoreDiv.textContent = '没有更多图片了';
                    imageContainer.appendChild(noMoreDiv);
                }
            } else {
                // 显示滚动提示
                const scrollHint = document.getElementById('scrollHint');
                if (scrollHint && allResults.length > pageSize) {
                    scrollHint.style.display = 'block';
                }
            }
        });
    }

    // 加载图片函数
    function loadImages(calligrapher, book) {
        // 添加详细调试日志
        console.log('调用loadImages函数:');
        console.log('- 书法家参数:', calligrapher);
        console.log('- 典籍参数:', book);
        console.log('- 字符:', charInfo.han);

        // 重置分页状态
        currentPage = 0;
        allResults = [];
        isLoading = false;
        hasMoreData = true;

        // 清空现有图片
        imageContainer.innerHTML = '';

        // 显示加载中
        const loading = document.createElement('div');
        loading.style.textAlign = 'center';
        loading.style.padding = '20px';
        loading.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                <div class="modal-spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 30px; height: 30px; animation: modal-spin 1s linear infinite;"></div>
                <div style="color: #666;">正在加载图片...</div>
            </div>
        `;
        
        // 确保模态框spinner动画样式存在
        if (!document.getElementById('modal-spinner-style')) {
            const style = document.createElement('style');
            style.id = 'modal-spinner-style';
            style.textContent = '@keyframes modal-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
            document.head.appendChild(style);
        }
        
        imageContainer.appendChild(loading);

        // 构建查询参数
        const queryParams = new URLSearchParams({
            han: charInfo.han,
            author: calligrapher || '',
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
                    allResults = data.results;
                    console.log(`总共找到${allResults.length}个结果`);
                    
                    // 加载第一页
                    loadMoreImages();
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
    modalBody.appendChild(scrollHint);
    modalContent.appendChild(modalBody);

    // 添加模态窗口到文档
    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // 添加滚动事件监听器实现滑动加载
    modalContent.addEventListener('scroll', function() {
        // 检查是否滚动到底部
        const scrollTop = modalContent.scrollTop;
        const scrollHeight = modalContent.scrollHeight;
        const clientHeight = modalContent.clientHeight;
        
        // 当滚动到距离底部50px时开始加载更多
        if (scrollTop + clientHeight >= scrollHeight - 50) {
            loadMoreImages();
        }
    });

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
    loadingDiv.innerHTML = '<div style="text-align: center;"><div class="export-spinner" style="border: 3px solid #f3f3f3;border-top: 3px solid #3498db;border-radius: 50%;width: 30px;height: 30px;margin: 0 auto 10px;"></div><div style="margin-top: 10px;">正在生成图片，请稍候...</div></div>';
    document.body.appendChild(loadingDiv);

    // 添加旋转动画，限制作用范围
    const style = document.createElement('style');
    style.textContent = '@keyframes export-spin {0% { transform: rotate(0deg); }100% { transform: rotate(360deg); }} .export-spinner { animation: export-spin 1s linear infinite; }';
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

        // 收集所有图片ID和每行字数
        const imageIds = [];
        const charContainers = document.querySelectorAll('#resultContainer .char-container, #resultContainer .missing-char');
        charContainers.forEach(container => {
            if (container.classList.contains('missing-char')) {
                // 处理缺失字符，添加占位符标识
                imageIds.push('placeholder');
                console.log('添加占位符标识到导出列表');
            } else {
                // 处理正常图片，从容器的数据属性中获取图片ID
                const imageId = container.getAttribute('data-image-id');
                if (imageId && imageId.trim() !== '') {
                    imageIds.push(imageId.trim());
                } else {
                    // 如果没有图片ID，使用占位符
                    imageIds.push('placeholder');
                    console.log('图片容器缺少图片ID，使用占位符');
                }
            }
        });

        console.log('收集到的图片ID数量:', imageIds.length);
        console.log('图片ID列表:', imageIds);

        // 如果没有收集到图片ID，显示错误信息
        if (imageIds.length === 0) {
            alert('没有找到可导出的图片，请先生成集字结果');
            return;
        }

        // 获取每行显示的字数
        const charsPerLine = parseInt(document.getElementById('charsPerLineInput').value) || 5;

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
        loadingDiv.innerHTML = '<div style="text-align: center;"><div class="export-spinner-2" style="border: 3px solid #f3f3f3;border-top: 3px solid #3498db;border-radius: 50%;width: 30px;height: 30px;margin: 0 auto 10px;"></div><div style="margin-top: 10px;">正在生成图片，请稍候...</div></div>';
        
        // 确保第二个导出spinner动画样式存在
        if (!document.getElementById('export-spinner-2-style')) {
            const style2 = document.createElement('style');
            style2.id = 'export-spinner-2-style';
            style2.textContent = '@keyframes export-spin-2 {0% { transform: rotate(0deg); }100% { transform: rotate(360deg); }} .export-spinner-2 { animation: export-spin-2 1s linear infinite; }';
            document.head.appendChild(style2);
        }
        document.body.appendChild(loadingDiv);

        // 发送请求到后端API
        // 获取当前选择的排列方向
        const directionSelect = document.getElementById('directionSelect');
        const direction = directionSelect ? directionSelect.value : 'horizontal';

        // 调试信息：确认占位符是否被包含
        console.log('准备发送到后端的图片ID数量:', imageIds.length);
        console.log('准备发送到后端的图片ID列表:', imageIds);
        const hasPlaceholder = imageIds.some(id => id === 'placeholder');
        console.log('发送的ID中是否包含占位符:', hasPlaceholder);

        fetch('/export_image_by_ids', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_ids: imageIds,
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
