document.addEventListener("DOMContentLoaded", () => {
    // 初始化设置页面
    initializeSettings();
    
    // 添加事件监听器
    addSettingsEventListeners();
});

// 初始化设置
function initializeSettings() {
    // 从localStorage加载已保存的设置
    loadSavedSettings();
}

// 加载已保存的设置
function loadSavedSettings() {
    // 深色模式
    const darkMode = localStorage.getItem('darkMode') === 'true';
    document.getElementById('darkModeToggle').checked = darkMode;
    
    // 字体大小
    const fontSize = localStorage.getItem('fontSize') || 'medium';
    document.getElementById('fontSizeSelect').value = fontSize;
    
    // 默认排列方式
    const defaultDirection = localStorage.getItem('defaultDirection') || 'horizontal';
    document.getElementById('defaultDirectionSelect').value = defaultDirection;
    
    // 默认每行字数
    const defaultCharsPerLine = localStorage.getItem('defaultCharsPerLine') || '10';
    document.getElementById('defaultCharsPerLine').value = defaultCharsPerLine;
    
    // 自动保存
    const autoSave = localStorage.getItem('autoSave') === 'true';
    document.getElementById('autoSaveToggle').checked = autoSave;
    
    // 图片缓存大小
    const imageCacheSize = localStorage.getItem('imageCacheSize') || '100';
    document.getElementById('imageCacheSize').value = imageCacheSize;
    
    // 预加载图片
    const preloadImages = localStorage.getItem('preloadImages') !== 'false';
    document.getElementById('preloadImagesToggle').checked = preloadImages;
}

// 添加设置功能的事件监听器
function addSettingsEventListeners() {
    // 深色模式切换
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', function() {
            showFeatureNotAvailable('深色模式');
            // 重置开关状态
            this.checked = false;
        });
    }
    
    // 字体大小选择
    const fontSizeSelect = document.getElementById('fontSizeSelect');
    if (fontSizeSelect) {
        fontSizeSelect.addEventListener('change', function() {
            showFeatureNotAvailable('字体大小设置');
            // 重置选择状态
            this.value = 'medium';
        });
    }
    
    // 默认排列方式
    const defaultDirectionSelect = document.getElementById('defaultDirectionSelect');
    if (defaultDirectionSelect) {
        defaultDirectionSelect.addEventListener('change', function() {
            showFeatureNotAvailable('默认排列方式设置');
            // 重置选择状态
            this.value = 'horizontal';
        });
    }
    
    // 默认每行字数
    const defaultCharsPerLine = document.getElementById('defaultCharsPerLine');
    if (defaultCharsPerLine) {
        defaultCharsPerLine.addEventListener('change', function() {
            showFeatureNotAvailable('默认每行字数设置');
            // 重置值
            this.value = '10';
        });
    }
    
    // 自动保存
    const autoSaveToggle = document.getElementById('autoSaveToggle');
    if (autoSaveToggle) {
        autoSaveToggle.addEventListener('change', function() {
            showFeatureNotAvailable('自动保存');
            // 重置开关状态
            this.checked = false;
        });
    }
    
    // 图片缓存大小
    const imageCacheSize = document.getElementById('imageCacheSize');
    if (imageCacheSize) {
        imageCacheSize.addEventListener('change', function() {
            showFeatureNotAvailable('图片缓存大小设置');
            // 重置选择状态
            this.value = '100';
        });
    }
    
    // 预加载图片
    const preloadImagesToggle = document.getElementById('preloadImagesToggle');
    if (preloadImagesToggle) {
        preloadImagesToggle.addEventListener('change', function() {
            showFeatureNotAvailable('预加载图片');
            // 重置开关状态
            this.checked = true;
        });
    }
    
    // 清除缓存按钮
    const clearCacheBtn = document.getElementById('clearCacheBtn');
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', function() {
            showFeatureNotAvailable('清除缓存');
        });
    }
    
    // 重置设置按钮
    const resetSettingsBtn = document.getElementById('resetSettingsBtn');
    if (resetSettingsBtn) {
        resetSettingsBtn.addEventListener('click', function() {
            showFeatureNotAvailable('重置设置');
        });
    }
}

// 显示功能暂未开放的提示
function showFeatureNotAvailable(featureName) {
    // 避免重复显示提示
    if (document.getElementById('feature-not-available-notification')) {
        return;
    }
    
    const notification = document.createElement('div');
    notification.id = 'feature-not-available-notification';
    notification.style.position = 'fixed';
    notification.style.top = '50%';
    notification.style.left = '50%';
    notification.style.transform = 'translate(-50%, -50%)';
    notification.style.padding = '25px 35px';
    notification.style.backgroundColor = '#fff';
    notification.style.border = '2px solid #007bff';
    notification.style.borderRadius = '12px';
    notification.style.zIndex = '10001';
    notification.style.boxShadow = '0 8px 32px rgba(0,0,0,0.15)';
    notification.style.fontSize = '16px';
    notification.style.textAlign = 'center';
    notification.style.maxWidth = '400px';
    notification.style.minWidth = '320px';
    notification.innerHTML = `
        <div style="color: #007bff; font-weight: bold; margin-bottom: 15px; font-size: 18px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 10px;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            功能开发中
        </div>
        <div style="color: #666; font-size: 15px; line-height: 1.5; margin-bottom: 20px;">
            <strong>${featureName}</strong> 功能正在紧张开发中
            <br>
            敬请期待后续版本更新
        </div>
        <button onclick="this.parentElement.remove()" style="
            padding: 10px 25px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 500;
            transition: background-color 0.2s;
        " onmouseover="this.style.backgroundColor='#0056b3'" onmouseout="this.style.backgroundColor='#007bff'">
            我知道了
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // 4秒后自动移除提示（如果用户没有点击确定按钮）
    setTimeout(() => {
        if (notification && notification.parentNode) {
            document.body.removeChild(notification);
        }
    }, 4000);
}

// 保存设置到localStorage
function saveSetting(key, value) {
    localStorage.setItem(key, value);
}

// 获取设置从localStorage
function getSetting(key, defaultValue = null) {
    return localStorage.getItem(key) || defaultValue;
}

// 重置所有设置
function resetAllSettings() {
    const settingsKeys = [
        'darkMode',
        'fontSize', 
        'defaultDirection',
        'defaultCharsPerLine',
        'autoSave',
        'imageCacheSize',
        'preloadImages'
    ];
    
    settingsKeys.forEach(key => {
        localStorage.removeItem(key);
    });
    
    // 重新加载设置
    loadSavedSettings();
}

// 清除应用缓存
function clearAppCache() {
    // 清除localStorage中的缓存数据
    const cacheKeys = Object.keys(localStorage).filter(key => 
        key.startsWith('cache_') || key.startsWith('img_')
    );
    
    cacheKeys.forEach(key => {
        localStorage.removeItem(key);
    });
    
    // 如果有其他缓存清理逻辑，可以在这里添加
}