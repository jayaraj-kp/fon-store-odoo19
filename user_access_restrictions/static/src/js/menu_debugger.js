/** @odoo-module **/
/**
 * UAR Menu Debugger — only active when ?uar_debug=1 is in the URL.
 * Open browser console and run: uarDebugMenus()
 * It will print all menu item texts so you can verify exact strings.
 */
window.uarDebugMenus = function () {
    const selectors = [
        ".o_menu_sections a",
        ".o_menu_sections span",
        ".o_menu_sections .o_nav_entry",
        ".o_menu_sections .o_dropdown_item",
        ".o_dropdown_menu a",
        ".o_dropdown_menu span",
        ".o_dropdown_menu li",
        "[role='menuitem']",
        "[role='menu'] a",
    ].join(", ");

    const all = document.querySelectorAll(selectors);
    console.group("[UAR] All menu texts found on page:");
    all.forEach((el) => {
        const t = (el.textContent || "").trim();
        if (t && t.length < 60) {
            console.log(`"${t.toLowerCase()}"`, el);
        }
    });
    console.groupEnd();
    console.log("[UAR] Total elements scanned:", all.length);
};

console.log("[UAR] Debug helper ready. Run uarDebugMenus() in console to see all menu texts.");
