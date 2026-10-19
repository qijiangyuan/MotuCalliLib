/* 页面公共行为与字库、收藏、工作区管理。所有动态文字通过 textContent 输出。 */
"use strict";
const Motu = (() => {
  const $ = (id) => document.getElementById(id);
  const defaults = {
    theme: "light",
    fontSize: "normal",
    defaultDirection: "horizontal",
    defaultCols: 4,
    autoDraft: true,
  };
  function read(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch {
      return fallback;
    }
  }
  function write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      toast("浏览器存储不可用，请及时保存作品");
      return false;
    }
  }
  function preferences() {
    return { ...defaults, ...read("moyan.preferences", {}) };
  }
  function applyPreferences() {
    const p = preferences();
    document.documentElement.dataset.theme = p.theme;
    document.documentElement.dataset.size = p.fontSize;
  }
  let toastTimer;
  function toast(message) {
    const box = $("toast");
    if (!box) return;
    box.textContent = message;
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (box.hidden = true), 4200);
  }
  async function api(url, options = {}) {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(45000),
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
    const data = await response
      .json()
      .catch(() => ({ message: "服务返回内容异常，请稍后重试" }));
    if (!response.ok || data.success === false)
      throw new Error(data.message || `请求失败 (${response.status})`);
    return data;
  }
  function element(tag, cls = "", text = "") {
    const node = document.createElement(tag);
    node.className = cls;
    if (text) node.textContent = text;
    return node;
  }
  function image(id, han, lazy = true) {
    const img = element("img");
    img.src = `/media/${id}`;
    img.alt = `${han}的书法字形`;
    img.loading = lazy ? "lazy" : "eager";
    img.addEventListener("error", () => {
      const failure = element("div", "image-failure", "原图暂不可用");
      failure.setAttribute("role", "img");
      failure.setAttribute("aria-label", `${han}的原图暂不可用`);
      img.replaceWith(failure);
    });
    return img;
  }
  function empty(container, title, hint = "") {
    container.replaceChildren();
    const block = element("div", "empty-state");
    block.append(element("h3", "", title), element("p", "", hint));
    container.append(block);
  }
  function confirmAction(message) {
    return new Promise((resolve) => {
      const dialog = $("confirmDialog");
      $("confirmText").textContent = message;
      dialog.returnValue = "cancel";
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "yes"), {
        once: true,
      });
      dialog.showModal();
    });
  }
  function pages(container, page, total, navigate) {
    container.replaceChildren();
    if (total <= 1) return;
    const add = (label, target, disabled = false, current = false) => {
      const btn = element("button", current ? "current" : "", label);
      btn.disabled = disabled;
      if (current) btn.setAttribute("aria-current", "page");
      btn.onclick = () => navigate(target);
      container.append(btn);
    };
    add("上一页", page - 1, page <= 1);
    [...new Set([1, page - 1, page, page + 1, total])]
      .filter((n) => n > 0 && n <= total)
      .forEach((n) => add(String(n), n, false, n === page));
    add("下一页", page + 1, page >= total);
    container.append(element("span", "", `第 ${page} / ${total} 页`));
  }
  let optionsPromise;
  function options() {
    return (optionsPromise ||= api("/api/options"));
  }
  function fill(id, items, placeholder) {
    const select = $(id);
    if (!select) return;
    const value = select.value;
    select.replaceChildren();
    if (placeholder) {
      const opt = element("option", "", placeholder);
      opt.value = "";
      select.append(opt);
    }
    items.forEach((item) => {
      const opt = element("option", "", item);
      opt.value = item;
      select.append(opt);
    });
    select.value = value;
  }
  const favoriteIds = new Set();
  async function loadFavorites() {
    const data = await api("/api/favorites");
    favoriteIds.clear();
    data.results.forEach((item) => favoriteIds.add(item.id));
    return data.results;
  }
  function favoriteButton(id, plain = false) {
    const button = element("button", plain ? "button secondary" : "favorite-button");
    function sync() {
      const saved = favoriteIds.has(id);
      button.textContent = plain
        ? saved
          ? "已收藏 · 取消"
          : "收藏字形"
        : saved
          ? "★"
          : "☆";
      button.title = saved ? "取消收藏" : "收藏字形";
      button.setAttribute("aria-label", button.title);
      button.setAttribute("aria-pressed", String(saved));
      button.classList.toggle("saved", saved);
    }
    sync();
    button.onclick = async (event) => {
      event.preventDefault();
      event.stopPropagation();
      button.disabled = true;
      try {
        const saved = favoriteIds.has(id);
        await api(`/api/favorites/${id}`, { method: saved ? "DELETE" : "PUT" });
        if (saved) favoriteIds.delete(id);
        else favoriteIds.add(id);
        sync();
        toast(saved ? "已取消收藏" : "已加入我的收藏");
      } catch (error) {
        toast(error.message);
      } finally {
        button.disabled = false;
      }
    };
    return button;
  }
  function glyphCard(item) {
    const card = element("article", "glyph-card");
    const link = element("a");
    link.href = `/view_all_images.html?glyph_id=${item.id}`;
    const picture = element("div", "glyph-picture");
    picture.append(
      item.image_ids.length
        ? image(item.image_ids[0], item.han)
        : element("div", "image-failure", "无图版"),
    );
    const info = element("div", "glyph-info");
    info.append(
      element("strong", "", item.han),
      element("span", "badge", item.font || "未分类"),
      element("p", "", item.author || "佚名"),
    );
    const book = element("p", "", item.book_title || "出处未录");
    book.title = item.book_title || "出处未录";
    info.append(book);
    link.append(picture, info);
    card.append(link, favoriteButton(item.id));
    return card;
  }
  applyPreferences();
  return {
    $,
    api,
    element,
    image,
    empty,
    toast,
    read,
    write,
    preferences,
    defaults,
    applyPreferences,
    confirmAction,
    pages,
    options,
    fill,
    loadFavorites,
    favoriteButton,
    glyphCard,
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  const { $, api, element, image, empty, toast } = Motu;
  document
    .querySelectorAll("dialog .dialog-close")
    .forEach((button) =>
      button.addEventListener("click", () => button.closest("dialog").close()),
    );
  const errorState = (container, error) => empty(container, "加载失败", error.message);
  async function home() {
    $("homeSearch").onsubmit = (event) => {
      event.preventDefault();
      location.href = `/library?han=${encodeURIComponent($("homeHan").value.trim())}`;
    };
    api("/api/statistics")
      .then((stats) =>
        ["glyphs", "images", "authors", "books"].forEach(
          (key, index) =>
            ($("statistics").children[index].querySelector("strong").textContent =
              stats[key].toLocaleString("zh-CN")),
        ),
      )
      .catch((error) => toast(error.message));
    const result = await api("/api/compose?text=" + encodeURIComponent("春和景明"));
    result.characters.forEach((item, index) => {
      if (item.image_id)
        $("heroGlyphs").children[index].replaceWith(
          image(item.image_id, item.han, false),
        );
    });
  }
  async function library() {
    let page = 1,
      favoritesOnly = false,
      revision = 0;
    const params = new URLSearchParams(location.search);
    ["han", "author", "book"].forEach(
      (key, index) =>
        ($(["searchHan", "authorFilter", "bookFilter"][index]).value =
          params.get(key) || ""),
    );
    await Promise.all([
      Motu.loadFavorites(),
      Motu.options().then((data) => {
        Motu.fill("fontFilter", data.fonts, "全部书体");
        Motu.fill("authorOptions", data.authors);
        Motu.fill("bookOptions", data.books);
        $("fontFilter").value = params.get("font") || "";
      }),
    ]);
    function updateChips() {
      $("hanChips").replaceChildren();
      const chars = [
        ...new Set([...$("searchHan").value.trim()].filter((c) => c.trim())),
      ];
      if (chars.length > 1)
        chars.forEach((char) => {
          const btn = element("button", "", char);
          btn.onclick = () => {
            $("searchHan").value = char;
            page = 1;
            search();
          };
          $("hanChips").append(btn);
        });
    }
    async function search() {
      const token = ++revision;
      empty($("glyphResults"), "正在检索字形…");
      $("pagination").replaceChildren();
      $("allGlyphs").classList.toggle("active", !favoritesOnly);
      $("favoriteGlyphs").classList.toggle("active", favoritesOnly);
      updateChips();
      try {
        const query = new URLSearchParams(new FormData($("librarySearch")));
        query.set("page", page);
        query.set("per_page", 24);
        let data;
        if (favoritesOnly) {
          let items = await Motu.loadFavorites();
          const han = $("searchHan").value.trim(),
            font = $("fontFilter").value,
            author = $("authorFilter").value.trim(),
            book = $("bookFilter").value.trim();
          items = items.filter(
            (x) =>
              (!han || han.includes(x.han)) &&
              (!font || x.font === font) &&
              (!author || x.author === author) &&
              (!book || x.book_title === book),
          );
          data = {
            results: items.slice((page - 1) * 24, page * 24),
            total: items.length,
            pages: Math.ceil(items.length / 24),
          };
        } else data = await api("/api/catalogue?" + query);
        if (token !== revision) return;
        history.replaceState(null, "", "/library?" + query);
        $("resultCount").textContent =
          `共 ${data.total.toLocaleString("zh-CN")} 条${favoritesOnly ? "收藏" : "字形"}记录`;
        $("glyphResults").replaceChildren(...data.results.map(Motu.glyphCard));
        if (!data.results.length)
          empty(
            $("glyphResults"),
            favoritesOnly ? "暂无匹配的收藏" : "没有找到相关字形",
            "试试减少筛选条件，或换用繁体、异体写法。",
          );
        Motu.pages($("pagination"), page, data.pages, (next) => {
          page = next;
          search();
          $("librarySearch").scrollIntoView({ behavior: "smooth" });
        });
      } catch (error) {
        if (token === revision) {
          errorState($("glyphResults"), error);
          $("resultCount").textContent = "检索失败";
        }
      }
    }
    $("librarySearch").onsubmit = (event) => {
      event.preventDefault();
      page = 1;
      search();
    };
    $("resetSearch").onclick = () => {
      $("librarySearch").reset();
      page = 1;
      search();
    };
    $("allGlyphs").onclick = () => {
      favoritesOnly = false;
      page = 1;
      search();
    };
    $("favoriteGlyphs").onclick = () => {
      favoritesOnly = true;
      page = 1;
      search();
    };
    page = Math.max(1, Number(params.get("page")) || 1);
    await search();
  }
  async function detail() {
    const id = new URLSearchParams(location.search).get("glyph_id");
    const [item] = await Promise.all([
      api(`/api/glyphs/${encodeURIComponent(id)}`),
      Motu.loadFavorites(),
    ]);
    const meta = element("div", "detail-meta");
    meta.append(
      element("h1", "", `${item.han} · ${item.font || "未分类"}`),
      element("p", "", `书法家：${item.author || "佚名"}`),
      element(
        "p",
        "",
        `典籍：${item.book_title || "出处未录"}　 ·　 ${item.image_count} 张图版`,
      ),
    );
    const actions = element("div", "actions"),
      link = element("a", "button primary", "用此字集字 ↗");
    link.href = "/calligraphy_set?text=" + encodeURIComponent(item.han);
    actions.append(Motu.favoriteButton(item.id, true), link);
    $("glyphDetail").replaceChildren(
      element("div", "detail-han", item.han),
      meta,
      actions,
    );
    let reportImageId = null;
    item.image_ids.forEach((imageId, index) => {
      const card = element("article", "detail-card"),
        button = element("button", "image-button");
      button.setAttribute("aria-label", `放大第 ${index + 1} 张字形图片`);
      button.append(image(imageId, item.han));
      button.onclick = () => {
        $("largeImage").src = `/media/${imageId}`;
        $("largeCaption").textContent =
          `${item.han} · ${item.author || "佚名"} · 图版 ${index + 1}`;
        $("imageDialog").showModal();
      };
      const caption = element("div", "detail-caption");
      caption.append(element("span", "", `图版 ${String(index + 1).padStart(2, "0")}`));
      const report = element("button", "", "纠错");
      report.onclick = () => {
        reportImageId = imageId;
        $("reportReason").value = "";
        $("reportDialog").showModal();
      };
      caption.append(report);
      card.append(button, caption);
      $("detailImages").append(card);
    });
    if (!item.image_ids.length) empty($("detailImages"), "暂无字形图片");
    $("reportForm").onsubmit = async (event) => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      try {
        await api("/api/feedback", {
          method: "POST",
          body: JSON.stringify({
            image_id: reportImageId,
            reason: $("reportReason").value,
          }),
        });
        $("reportDialog").close();
        toast("纠错记录已保存，可在设置中查看");
      } catch (error) {
        toast(error.message);
      } finally {
        button.disabled = false;
      }
    };
  }
  async function works() {
    const directions = {
      horizontal: "横排左起",
      "horizontal-reverse": "横排右起",
      "vertical-left": "竖排左起",
      "vertical-right": "竖排右起",
    };
    async function load() {
      try {
        const data = await api(
          "/api/works?q=" + encodeURIComponent($("workQuery").value),
        );
        $("workCount").textContent = `共 ${data.works.length} 件作品`;
        $("worksGrid").replaceChildren();
        data.works.forEach((work) => {
          const card = element("article", "work-card"),
            preview = element("a", "work-preview");
          preview.href = `/calligraphy_set?work=${work.id}`;
          preview.setAttribute("aria-label", `打开作品 ${work.title}`);
          work.characters
            .slice(0, 4)
            .forEach((char) =>
              preview.append(
                char.image_id
                  ? image(char.image_id, char.han)
                  : element("span", "", char.han),
              ),
            );
          const content = element("div", "work-card-content");
          content.append(
            element("h2", "", work.title),
            element(
              "p",
              "",
              `${work.characters.length} 字 · ${directions[work.direction]} · ${new Date(work.updated_at).toLocaleDateString("zh-CN")} 更新`,
            ),
          );
          const actions = element("div", "actions"),
            edit = element("a", "button secondary", "继续创作 ↗"),
            remove = element("button", "button subtle", "删除");
          edit.href = preview.href;
          remove.onclick = async () => {
            if (
              !(await Motu.confirmAction(
                `删除作品“${work.title}”？建议先在设置中导出备份。`,
              ))
            )
              return;
            try {
              await api(`/api/works/${work.id}`, { method: "DELETE" });
              await load();
              toast("作品已删除");
            } catch (error) {
              toast(error.message);
            }
          };
          actions.append(edit, remove);
          content.append(actions);
          card.append(preview, content);
          $("worksGrid").append(card);
        });
        if (!data.works.length)
          empty(
            $("worksGrid"),
            "这里还没有作品",
            "前往集字创作，保存你的第一件作品；也可清空搜索条件。",
          );
      } catch (error) {
        errorState($("worksGrid"), error);
      }
    }
    $("workSearch").onsubmit = (event) => {
      event.preventDefault();
      load();
    };
    await load();
  }
  async function settings() {
    function loadPreferences() {
      const pref = Motu.preferences();
      Object.keys(Motu.defaults).forEach((key) => {
        if ($(key).type === "checkbox") $(key).checked = pref[key];
        else $(key).value = pref[key];
      });
    }
    loadPreferences();
    $("settingsForm").onchange = () => {
      if (!$("settingsForm").reportValidity()) return;
      const prefs = {};
      Object.keys(Motu.defaults).forEach(
        (key) =>
          (prefs[key] =
            $(key).type === "checkbox"
              ? $(key).checked
              : $(key).type === "number"
                ? Number($(key).value)
                : $(key).value),
      );
      Motu.write("moyan.preferences", prefs);
      Motu.applyPreferences();
      toast("偏好已保存");
    };
    $("resetPreferences").onclick = async () => {
      if (
        !(await Motu.confirmAction(
          "恢复默认的阅读与创作偏好？已保存作品和草稿会保留。",
        ))
      )
        return;
      Motu.write("moyan.preferences", Motu.defaults);
      loadPreferences();
      Motu.applyPreferences();
      toast("已恢复默认偏好");
    };
    $("restoreFile").onchange = async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      try {
        if (file.size > 8 * 1024 * 1024) throw new Error("备份文件超过 8 MB");
        const data = JSON.parse(await file.text());
        if (
          !(await Motu.confirmAction(
            "将备份中的作品、收藏和纠错合并到当前工作区？现有作品会保留。",
          ))
        )
          return;
        const result = await api("/api/restore", {
          method: "POST",
          body: JSON.stringify(data),
        });
        toast(result.message);
        await reports();
      } catch (error) {
        toast(
          error instanceof SyntaxError ? "文件不是有效的 JSON 备份" : error.message,
        );
      } finally {
        event.target.value = "";
      }
    };
    api("/api/statistics")
      .then(
        (stats) =>
          ($("systemStats").textContent =
            `${stats.characters.toLocaleString("zh-CN")} 个不同汉字 · ${stats.fonts} 类书体 · ${stats.works} 件作品`),
      )
      .catch((error) => ($("systemStats").textContent = error.message));
    async function reports() {
      const data = await api("/api/feedback");
      $("reportsList").replaceChildren();
      data.reports.forEach((report) => {
        const row = element("div", "feedback-item"),
          copy = element("div");
        copy.append(
          element("p", "", `${report.han} · ${report.reason}`),
          element(
            "small",
            "",
            `图版 ${report.image_id} · ${report.created_at} · ${report.status === "reviewed" ? "已核查" : "待核查"}`,
          ),
        );
        const button = element(
          "button",
          "button secondary",
          report.status === "reviewed" ? "重新待核查" : "标记已核查",
        );
        button.onclick = async () => {
          try {
            await api(`/api/feedback/${report.id}`, {
              method: "PATCH",
              body: JSON.stringify({
                status: report.status === "reviewed" ? "pending" : "reviewed",
              }),
            });
            await reports();
          } catch (error) {
            toast(error.message);
          }
        };
        row.append(copy, button);
        $("reportsList").append(row);
      });
      if (!data.reports.length)
        empty($("reportsList"), "暂无纠错记录", "在字形详情页面记录需要核查的图版。");
    }
    $("refreshReports").onclick = () =>
      reports().catch((error) => toast(error.message));
    await reports();
  }
  const start = $("glyphDetail")
    ? detail
    : { home, library, works, settings }[document.body.dataset.page];
  if (start)
    start().catch((error) => {
      toast(error.message);
      const container = $("glyphDetail") || $("glyphResults");
      if (container) errorState(container, error);
    });
});
