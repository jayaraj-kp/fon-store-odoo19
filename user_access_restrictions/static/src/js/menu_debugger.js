///** @odoo-module **/
///**
// * UAR Menu Debugger — only active when ?uar_debug=1 is in the URL.
// * Open browser console and run: uarDebugMenus()
// * It will print all menu item texts so you can verify exact strings.
// */
//window.uarDebugMenus = function () {
//    const selectors = [
//        ".o_menu_sections a",
//        ".o_menu_sections span",
//        ".o_menu_sections .o_nav_entry",
//        ".o_menu_sections .o_dropdown_item",
//        ".o_dropdown_menu a",
//        ".o_dropdown_menu span",
//        ".o_dropdown_menu li",
//        "[role='menuitem']",
//        "[role='menu'] a",
//    ].join(", ");
//
//    const all = document.querySelectorAll(selectors);
//    console.group("[UAR] All menu texts found on page:");
//    all.forEach((el) => {
//        const t = (el.textContent || "").trim();
//        if (t && t.length < 60) {
//            console.log(`"${t.toLowerCase()}"`, el);
//        }
//    });
//    console.groupEnd();
//    console.log("[UAR] Total elements scanned:", all.length);
//};
//
//console.log("[UAR] Debug helper ready. Run uarDebugMenus() in console to see all menu texts.");
/** @odoo-module **/
/**
 * UAR Menu Debugger v2 — shows direct text + data-menu-xmlid for every menu element.
 * Run in browser console: uarDebugMenus()
 */

function getDirectText(el) {
    let text = "";
    el.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) text += node.textContent;
    });
    return text.trim();
}

window.uarDebugMenus = function () {
    console.group("[UAR] === TOP-LEVEL NAVBAR items (these should NEVER be hidden) ===");
    document.querySelectorAll(".o_main_navbar [role='menuitem'], .o_menu_brand").forEach((el) => {
        const direct = getDirectText(el);
        const xmlid = el.getAttribute("data-menu-xmlid") || "";
        if (direct) console.log(`NAVBAR: "${direct.toLowerCase()}"`, xmlid ? `xmlid: ${xmlid}` : "", el);
    });
    console.groupEnd();

    console.group("[UAR] === DROPDOWN items (these are safe to hide) ===");
    document.querySelectorAll(
        ".o_dropdown_menu a, .o_dropdown_menu li > span, .dropdown-menu a, .dropdown-menu li > span"
    ).forEach((el) => {
        const direct = getDirectText(el);
        const xmlid = el.getAttribute("data-menu-xmlid") || "";
        if (direct && direct.length < 60) {
            console.log(`DROPDOWN: "${direct.toLowerCase()}"`, xmlid ? `xmlid: ${xmlid}` : "", el);
        }
    });
    console.groupEnd();

    console.group("[UAR] === All [data-menu-xmlid] items ===");
    document.querySelectorAll("[data-menu-xmlid]").forEach((el) => {
        const direct = getDirectText(el);
        const xmlid = el.getAttribute("data-menu-xmlid");
        console.log(`xmlid="${xmlid}" text="${direct.toLowerCase()}"`, el);
    });
    console.groupEnd();

    console.log("[UAR] Debug complete. Expand groups above to inspect.");
};

console.log("[UAR] Debug v2 ready. Run uarDebugMenus() in console.");