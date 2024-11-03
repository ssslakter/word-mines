document.addEventListener("DOMContentLoaded", () => {
    theme_box = document.getElementById("theme");
    theme_box.checked = localStorage.getItem("theme") == "dark";
    changeTheme(theme_box.checked);
})

function changeTheme(is_dark)
{
    theme = localStorage.getItem("theme") || document.body.getAttribute("data-theme");
    new_theme = is_dark ? "dark" : "light";
    document.body.setAttribute("data-theme", new_theme);
    localStorage.setItem("theme", new_theme);    
}