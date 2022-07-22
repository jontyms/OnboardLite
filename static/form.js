// Other dropdown logic

let dropdowns = document.querySelectorAll("select");

for (let i = 0; i < dropdowns.length; i++) {
    dropdowns[i].onchange = evt => {
        let el = evt.target;
        if (el.value == "_other") {
            el.parentElement.querySelector(".other_dropdown").style.display = "block";
        } else {
            el.parentElement.querySelector(".other_dropdown").style.display = "none";
        }
    }
}

// todo: submit logic
// - must account for Other option in dropdown
// - make sure we do server-side validation