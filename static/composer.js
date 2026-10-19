"use strict";
document.addEventListener("DOMContentLoaded", async () => {
  const { $, api, element, image, empty, toast } = Motu;
  const pref = Motu.preferences();
  let characters = [],
    workId = null,
    dirty = false,
    generatedText = "",
    generating = false;
  let selectionIndex = 0,
    selectionPage = 1,
    selectionRevision = 0;
  const hanOnly = (text) =>
    [...text]
      .filter((char) =>
        /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u{20000}-\u{323af}]/u.test(char),
      )
      .join("");
  $("direction").value = pref.defaultDirection;
  $("cols").value = pref.defaultCols;
  function state() {
    return {
      id: workId,
      title: $("workTitle").value,
      text: $("composeText").value,
      generatedText,
      characters,
      direction: $("direction").value,
      cols: Number($("cols").value),
      filters: {
        font: $("composeFont").value,
        calligrapher: $("composeAuthor").value,
        book: $("composeBook").value,
      },
      size: Number($("exportSize").value),
      gap: Number($("exportGap").value),
      background: $("background").value,
    };
  }
  function draft() {
    if (Motu.preferences().autoDraft) Motu.write("moyan.draft", state());
  }
  function changed() {
    dirty = true;
    $("saveStatus").textContent = "有未保存的修改";
    draft();
    updateButtons();
  }
  function updateButtons() {
    const valid =
      characters.length > 0 &&
      hanOnly($("composeText").value) === generatedText &&
      !generating;
    $("saveWork").disabled = !valid;
    $("exportWork").disabled = !valid || characters.some((c) => !c.image_id);
  }
  function restore(value) {
    if (
      !value ||
      typeof value !== "object" ||
      !Array.isArray(value.characters) ||
      value.characters.length > 200
    )
      throw new Error("草稿格式无效，请新建作品");
    workId = value.id || null;
    characters = value.characters;
    generatedText = value.generatedText ?? value.text;
    $("workTitle").value = value.title || "";
    $("composeText").value = value.text || "";
    $("direction").value = value.direction || pref.defaultDirection;
    $("cols").value = value.cols || pref.defaultCols;
    $("composeFont").value = value.filters?.font || "";
    $("composeAuthor").value = value.filters?.calligrapher || "";
    $("composeBook").value = value.filters?.book || "";
    $("exportSize").value = value.size || 240;
    $("exportGap").value = value.gap ?? 12;
    $("background").value = value.background || "white";
    count();
    render();
  }
  function count() {
    $("textCount").textContent = `${[...hanOnly($("composeText").value)].length} / 200`;
  }
  function render() {
    const canvas = $("compositionCanvas");
    canvas.replaceChildren();
    const missing = [
      ...new Set(characters.filter((c) => !c.image_id).map((c) => c.han)),
    ];
    $("missingNotice").hidden = !missing.length;
    $("missingNotice").textContent =
      `缺字：${missing.join("、")}。点击缺字格放宽条件选字，补齐后即可导出。`;
    if (!characters.length) {
      canvas.className = "composition-canvas";
      empty(canvas, "落笔之前，先选一段诗文", "生成后点击任意字形，即可挑选其他写法。");
      $("composeStatus").textContent = "从左侧输入第一句文字";
      updateButtons();
      return;
    }
    const cols = Math.max(1, Math.min(20, Number($("cols").value) || 4));
    const direction = $("direction").value;
    const vertical = direction.startsWith("vertical");
    const across = vertical
      ? Math.ceil(characters.length / cols)
      : Math.min(cols, characters.length);
    canvas.className = "composition-canvas composition-grid";
    canvas.style.gridTemplateColumns = `repeat(${across}, auto)`;
    canvas.style.background = {
      white: "#fff",
      paper: "#f4eedf",
      transparent: "transparent",
    }[$("background").value];
    characters.forEach((char, index) => {
      const cell = element(
        "button",
        "composition-cell" + (!char.image_id ? " missing" : ""),
      );
      cell.setAttribute("aria-label", `替换第 ${index + 1} 字 ${char.han}`);
      cell.title = `${char.han} · ${char.author || "点击选择字形"}`;
      if (char.image_id) cell.append(image(char.image_id, char.han, false));
      else cell.textContent = char.han;
      cell.append(element("span", "", String(index + 1)));
      let col, row;
      if (vertical) {
        col = Math.floor(index / cols);
        row = index % cols;
        if (direction === "vertical-right") col = across - 1 - col;
      } else {
        row = Math.floor(index / cols);
        col = index % cols;
        if (direction === "horizontal-reverse") col = across - 1 - col;
      }
      cell.style.gridColumn = col + 1;
      cell.style.gridRow = row + 1;
      cell.onclick = () => {
        selectionIndex = index;
        selectionPage = 1;
        $("selectionTitle").textContent =
          `为“${char.han}”选择写法 · 第 ${index + 1} 字`;
        $("selectFont").value = $("composeFont").value;
        $("selectAuthor").value = $("composeAuthor").value;
        $("selectionDialog").showModal();
        loadSelection();
      };
      canvas.append(cell);
    });
    $("composeStatus").textContent =
      `${characters.length} 字 · 已选 ${characters.filter((c) => c.image_id).length} 字 · 点击字格替换写法`;
    updateButtons();
  }
  async function loadSelection() {
    const revision = ++selectionRevision;
    empty($("selectionResults"), "正在查找可用字形…");
    $("selectionPages").replaceChildren();
    try {
      const query = new URLSearchParams({
        han: characters[selectionIndex].han,
        font: $("selectFont").value,
        author: $("selectAuthor").value.trim(),
        per_page: 10,
        page: selectionPage,
      });
      const data = await api("/api/catalogue?" + query);
      const details = await Promise.all(
        data.results.map((item) => api(`/api/glyphs/${item.id}`)),
      );
      if (revision !== selectionRevision) return;
      $("selectionResults").replaceChildren();
      details.forEach((item) =>
        item.image_ids.forEach((id) => {
          const card = element("button", "selection-card");
          card.type = "button";
          card.append(
            image(id, item.han),
            element("span", "", `${item.font || "未分类"} · ${item.author || "佚名"}`),
            element("span", "muted", item.book_title || "出处未录"),
          );
          card.setAttribute(
            "aria-label",
            `选用 ${item.han} ${item.author || "佚名"} 图版 ${id}`,
          );
          card.onclick = () => {
            characters[selectionIndex] = { ...item, glyph_id: item.id, image_id: id };
            $("selectionDialog").close();
            render();
            changed();
            toast("已替换当前字形");
          };
          $("selectionResults").append(card);
        }),
      );
      if (!$("selectionResults").children.length)
        empty(
          $("selectionResults"),
          "该条件下没有字形",
          "请选择全部书体或清空书家后重试。",
        );
      Motu.pages($("selectionPages"), selectionPage, data.pages, (page) => {
        selectionPage = page;
        loadSelection();
        $("selectionDialog").scrollTo({ top: 0 });
      });
    } catch (error) {
      if (revision === selectionRevision)
        empty($("selectionResults"), "选字加载失败", error.message);
    }
  }
  $("selectionForm").onsubmit = (event) => {
    event.preventDefault();
    selectionPage = 1;
    loadSelection();
  };
  $("composeForm").onsubmit = async (event) => {
    event.preventDefault();
    if (generating) return;
    const text = hanOnly($("composeText").value);
    if (!text || [...text].length > 200) return toast("请输入 1 至 200 个汉字");
    if (
      characters.length &&
      !(await Motu.confirmAction("重新生成会替换当前选字，作品名称和排版设置会保留。"))
    )
      return;
    generating = true;
    $("generateBtn").disabled = true;
    $("generateBtn").textContent = "正在生成…";
    updateButtons();
    try {
      const query = new URLSearchParams({
        text,
        font: $("composeFont").value,
        calligrapher: $("composeAuthor").value.trim(),
        book: $("composeBook").value.trim(),
      });
      const data = await api("/api/compose?" + query);
      characters = data.characters;
      generatedText = data.text;
      $("composeText").value = data.text;
      count();
      render();
      changed();
    } catch (error) {
      toast(error.message);
    } finally {
      generating = false;
      $("generateBtn").disabled = false;
      $("generateBtn").textContent = "生成集字 →";
      updateButtons();
    }
  };
  $("composeText").oninput = () => {
    count();
    changed();
    if (characters.length && hanOnly($("composeText").value) !== generatedText)
      $("composeStatus").textContent = "文字已修改，请重新生成后保存或导出";
  };
  $("workTitle").oninput = changed;
  ["direction", "cols", "background"].forEach(
    (id) =>
      ($(id).onchange = () => {
        if (!$(id).reportValidity()) return;
        render();
        changed();
      }),
  );
  ["exportSize", "exportGap", "composeFont", "composeAuthor", "composeBook"].forEach(
    (id) =>
      ($(id).onchange = () => {
        if ($(id).reportValidity()) changed();
      }),
  );
  document.querySelectorAll("[data-poem]").forEach(
    (button) =>
      (button.onclick = () => {
        $("composeText").value = button.dataset.poem;
        count();
        changed();
      }),
  );
  $("clearWork").onclick = async () => {
    if (
      (dirty || characters.length) &&
      !(await Motu.confirmAction("新建作品将清空当前编辑内容，已保存作品会保留。"))
    )
      return;
    workId = null;
    characters = [];
    generatedText = "";
    $("composeForm").reset();
    $("direction").value = pref.defaultDirection;
    $("cols").value = pref.defaultCols;
    dirty = false;
    history.replaceState(null, "", "/calligraphy_set");
    $("saveStatus").textContent = "作品尚未保存";
    count();
    render();
    draft();
  };
  $("saveWork").onclick = async () => {
    if (!$("cols").reportValidity()) return;
    const button = $("saveWork");
    button.disabled = true;
    try {
      const value = state();
      value.text = generatedText;
      const data = await api(workId ? `/api/works/${workId}` : "/api/works", {
        method: workId ? "PUT" : "POST",
        body: JSON.stringify(value),
      });
      workId = data.work.id;
      $("workTitle").value = data.work.title;
      dirty = false;
      history.replaceState(null, "", `/calligraphy_set?work=${workId}`);
      $("saveStatus").textContent = "已保存至我的作品";
      draft();
      toast("作品已保存");
    } catch (error) {
      toast(error.message);
    } finally {
      updateButtons();
    }
  };
  $("exportWork").onclick = async () => {
    if (!$("cols").reportValidity() || !$("exportGap").reportValidity()) return;
    const button = $("exportWork");
    button.disabled = true;
    button.textContent = "正在导出…";
    try {
      const value = state();
      const response = await fetch("/api/export", {
        method: "POST",
        signal: AbortSignal.timeout(60000),
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...value,
          image_ids: characters.map((c) => c.image_id),
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || "图片导出失败");
      }
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        link = element("a");
      link.href = url;
      link.download = `${($("workTitle").value || generatedText.slice(0, 12)).replace(/[<>:"/\\|?*]/g, "_")}.png`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast("图片已生成，请查看浏览器下载");
    } catch (error) {
      toast(error.message);
    } finally {
      button.textContent = "导出 PNG ↓";
      updateButtons();
    }
  };
  window.addEventListener("beforeunload", (event) => {
    if (dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  try {
    const options = await Motu.options();
    Motu.fill("composeFont", options.fonts, "全部书体");
    Motu.fill("selectFont", options.fonts, "全部书体");
    Motu.fill("composeAuthors", options.authors);
    Motu.fill("composeBooks", options.books);
    const params = new URLSearchParams(location.search);
    if (params.has("work")) {
      const data = await api(`/api/works/${encodeURIComponent(params.get("work"))}`);
      restore(data.work);
      $("saveStatus").textContent = "已打开保存的作品";
    } else if (params.has("text")) {
      $("composeText").value = params.get("text");
      count();
    } else {
      const saved = Motu.read("moyan.draft", null);
      if (pref.autoDraft && saved && (saved.text || saved.characters?.length)) {
        restore(saved);
        dirty = true;
        $("saveStatus").textContent = "已恢复浏览器草稿，请保存作品";
      }
    }
  } catch (error) {
    toast(error.message);
  }
});
