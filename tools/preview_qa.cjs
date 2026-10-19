// 对实际 Flask 页面运行浏览器验收并保存原始界面截图。
const { chromium } = require(
  process.env.PLAYWRIGHT_MODULE ||
    "C:/Users/86708/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
);
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const out = path.join(root, "tmp", "qa");
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const base = process.env.MOTU_PREVIEW_URL || "http://127.0.0.1:5055";
  const checks = [];
  page.on("dialog", (dialog) => dialog.accept());
  const shot = async (name, fullPage = false) => {
    if (!await page.locator('dialog[open]').count()) await page.evaluate(() => scrollTo(0, 0));
    await page.waitForFunction(() => [...document.querySelectorAll('img')].filter(i => {
      const r = i.getBoundingClientRect();
      return r.top < innerHeight && r.bottom > 0 && r.width > 0;
    }).every(i => i.complete));
    await page.screenshot({ path: path.join(out, name + ".png"), fullPage });
  };
  await page.goto(base + "/");
  await page.waitForFunction(
    () => document.querySelector("#statistics strong").textContent !== "—",
  );
  await page.locator("#heroGlyphs img").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll("#heroGlyphs img")].every((i) => i.complete),
  );
  await shot("home", true);
  await page.goto(base + "/library?han=" + encodeURIComponent("永"));
  await page.locator(".glyph-card").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".glyph-card img")]
      .slice(0, 12)
      .every((i) => i.complete),
  );
  await shot("library");
  if (await page.locator(".favorite-button").first().getAttribute('aria-pressed') !== 'true')
    await page.locator(".favorite-button").first().click();
  await page.waitForFunction(
    () =>
      document.querySelector(".favorite-button").getAttribute("aria-pressed") ===
      "true",
  );
  await page.locator("#favoriteGlyphs").click();
  await page.waitForFunction(() =>
    document.querySelector("#resultCount").textContent.includes("收藏"),
  );
  await shot("favorites");
  checks.push("收藏写入与检索");
  await page.locator(".glyph-card > a").first().click();
  await page.locator(".detail-card").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".detail-card img")]
      .slice(0, 5)
      .every((i) => i.complete),
  );
  await shot("detail");
  await page.locator(".image-button").first().click();
  await page.waitForFunction(() => document.querySelector("#largeImage").complete);
  await shot("image_zoom");
  await page.locator("#imageDialog .dialog-close").click();
  await page.locator(".detail-caption button").first().click();
  await page.locator("#reportReason").fill("操作演示：此图版的出处待人工核查。");
  await shot("feedback");
  await page.locator("#reportForm button[type=submit]").click();
  await page.waitForFunction(() => !document.querySelector("#reportDialog").open);
  checks.push("详情放大与纠错保存");
  await page.goto(base + "/calligraphy_set");
  await page.locator('#composeFont option[value="楷"]').waitFor({ state: "attached" });
  await page.locator("#workTitle").fill("春和景明");
  await page.locator("#composeText").fill("春和景明惠风和畅");
  await page.locator("#generateBtn").click();
  await page.locator(".composition-cell").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".composition-cell img")].every((i) => i.complete),
  );
  await shot("compose_horizontal", true);
  await page.locator(".composition-cell").first().click();
  await page.locator(".selection-card").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".selection-card img")]
      .slice(0, 5)
      .every((i) => i.complete),
  );
  await shot("selection");
  await page.locator(".selection-card").nth(1).click();
  await page.locator("#direction").selectOption("vertical-right");
  await page.locator("#cols").fill("4");
  await page.locator("#cols").dispatchEvent("change");
  await page.locator("#saveWork").click();
  await page.waitForFunction(() =>
    document.querySelector("#saveStatus").textContent.includes("已保存"),
  );
  const savedUrl = page.url();
  const beforeReload = await page
    .locator(".composition-cell img")
    .first()
    .getAttribute("src");
  await shot("compose_vertical", true);
  await page.reload();
  await page.locator(".composition-cell img").first().waitFor();
  if (
    (await page.locator(".composition-cell img").first().getAttribute("src")) !==
    beforeReload
  )
    throw new Error("选字保存后刷新不一致");
  checks.push("文字生成、逐字替换、竖排、保存后刷新恢复");
  const download = page.waitForEvent("download");
  await page.locator("#exportWork").click();
  await (await download).saveAs(path.join(out, "exported_work.png"));
  checks.push("真实远程图版 PNG 导出");
  await page.goto(base + "/works");
  await page.locator(".work-card").first().waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll(".work-preview img")].every((i) => i.complete),
  );
  await shot("works");
  await page.locator("#workQuery").fill("不存在的作品");
  await page.locator("#workSearch button").click();
  await page.waitForFunction(() =>
    document.querySelector("#workCount").textContent.includes("0"),
  );
  checks.push("作品搜索空结果");
  await page.goto(base + "/settings");
  await page.locator(".feedback-item").first().waitFor();
  if ((await page.locator(".feedback-item button").first().textContent()).includes('标记'))
    await page.locator(".feedback-item button").first().click();
  await page.waitForFunction(() =>
    document.querySelector(".feedback-item small").textContent.includes("已核查"),
  );
  await shot("settings", true);
  const backup = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出备份" }).click();
  await (await backup).saveAs(path.join(out, "workspace-backup.json"));
  await page
    .locator("#restoreFile")
    .setInputFiles(path.join(out, "workspace-backup.json"));
  await page.locator("#confirmDialog button[value=yes]").click();
  await page.waitForFunction(() =>
    document.querySelector("#toast").textContent.includes("恢复完成"),
  );
  checks.push("备份下载与合并恢复");
  await page.locator("#theme").selectOption("dark");
  await page.goto(base + "/library?han=" + encodeURIComponent("永"));
  await page.locator(".glyph-card").first().waitFor();
  if ((await page.locator("html").getAttribute("data-theme")) !== "dark")
    throw new Error("主题跨页面未生效");
  await shot("dark_library");
  checks.push("深色主题跨页面持久化");
  await page.goto(base + "/settings");
  await page.locator("#theme").selectOption("light");
  await page.goto(base + "/help");
  await shot("help");
  await page.goto(base + "/library?han=" + encodeURIComponent("龘"));
  await page.locator("#glyphResults .empty-state").waitFor();
  await shot("empty_search");
  await page.goto(base + "/calligraphy_set?text=" + encodeURIComponent("春龘"));
  await page.locator("#generateBtn").click();
  await page.locator("#missingNotice:not([hidden])").waitFor();
  if (!(await page.locator("#exportWork").isDisabled()))
    throw new Error("缺字时未阻止导出");
  await shot("missing");
  checks.push("缺字提示与阻止不完整导出");
  await page.reload();
  await page.locator("#generateBtn").waitFor();
  await page.goto(base + "/calligraphy_set");
  await page.locator("#missingNotice:not([hidden])").waitFor();
  checks.push("浏览器草稿恢复");
  await page.goto(savedUrl);
  await page.locator(".composition-cell").first().waitFor();
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
  });
  const phone = await mobile.newPage();
  const mobileChecks = [];
  for (const [name, route] of [
    ["mobile_home", "/"],
    ["mobile_library", "/library?han=永"],
    ["mobile_compose", new URL(savedUrl).pathname + new URL(savedUrl).search],
    ["mobile_settings", "/settings"],
  ]) {
    await phone.goto(base + route);
    if (name === "mobile_library") await phone.locator(".glyph-card").first().waitFor();
    if (name === "mobile_compose")
      await phone.locator(".composition-cell").first().waitFor();
    const overflow = await phone.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    );
    if (overflow) throw new Error(name + " 页面存在横向溢出");
    await phone.screenshot({ path: path.join(out, name + ".png"), fullPage: true });
    mobileChecks.push(name);
  }
  const result = {
    errors,
    checks,
    mobileChecks,
    savedUrl,
    title: await page.title(),
    captured_at: new Date().toISOString(),
  };
  fs.writeFileSync(
    path.join(out, "browser_acceptance.json"),
    JSON.stringify(result, null, 2),
  );
  if (errors.length) throw new Error(errors.join("\n"));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
