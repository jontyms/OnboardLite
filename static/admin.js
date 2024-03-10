let userDict = {};
let userList;
let qrScanner;

function load() {
    let valueNames = ["Name", "Status", "NID", "Discord", "Email", "Experience", "Major", "Mentee", "Details"];
    let valueItems = "<tr>";
    let valueHeader = "<tr>";
    for (let i = 0; i < valueNames.length; i++) {
        valueItems += `<td class="${valueNames[i].toLowerCase()}"></td>`;
        valueHeader += `<td><button class="sort totally_text" data-sort="${valueNames[i].toLowerCase()}">${valueNames[i]}</button></td>`
        valueNames[i] = valueNames[i].toLowerCase();
    }
    valueItems += "</tr>";
    valueHeader += "</tr>";

    document.querySelector("thead").innerHTML = valueHeader;

    const options = {
        valueNames: valueNames,
        item: valueItems,
        searchColumns: ["name", "nid", "discord", "email", "major", "status"]
    };

    let members = [];
    let count_full_member = 0;
    let count_all = 0;

    fetch("/admin/list").then(data => {
        return data.json();
    }).then(data2 => {
        data2 = data2.data;
        for (let i = 0; i < data2.length; i++) {
            member = data2[i];

            let userStatus = userStatusString(member);
            let userEntry = {
                "id": sanitizeHTML(member.id).replaceAll("&#45;", "-"),
                "name": sanitizeHTML(member.first_name + " " + member.surname),
                "status": userStatus,
                "discord": "@" + sanitizeHTML(member.discord.username),
                "email": sanitizeHTML(member.email),
                "nid": sanitizeHTML(member.nid),
                "experience": sanitizeHTML(member.experience),
                "major": sanitizeHTML(member.major),
                "details": `<button class="searchbtn btn" onclick="showUser('${sickoModeSanitize(member.id)}')">Details</a>`,
                "is_full_member": Boolean(member.is_full_member),
                "mentee": (member.mentee && member.mentee.domain_interest) ? member.mentee.domain_interest : "Not Mentee"
            }

            count_all++;
            if (member.is_full_member)
                count_full_member++;

            members.push(userEntry);

            member.name = member.first_name + " " + member.surname;
            member.username = "@" + member.discord.username;
            member.pfp = member.discord.avatar;
            member.status = userStatus;
            userDict[sickoModeSanitize(member.id)] = member;
        }

        userList = new List('users', options, members);

        document.querySelector(".right").innerHTML += `<br>${count_full_member} dues-paying, ${count_all} total`;
    })
}

function userStatusString(member) {
    if (member.sudo)
        return "Administrator";

    if (member.cyberlab_monitor.signtime !== 0)
        return "CyberLab Monitor";

    if (member.ops_email)
        return "Operations Member";

    if (member.is_full_member)
        return "Dues-Paying Member";

    if (!member.did_pay_dues)
        return "Needs Dues Payment";

    if (!member.ethics_form.signtime !== 0)
        return "Needs Ethics Form";

    return "Attendee"; // Unactivated account
}

// Sanitizes any non-alphanum.
function sickoModeSanitize(val) {
    return val.replaceAll(/[^\w\-]/g, "");
}

/**
 * Sanitize and encode all HTML in a user-submitted string
 * https://portswigger.net/web-security/cross-site-scripting/preventing
 * Needed because our table-searching library is circumstantially vulnerable to XSS.
 * @param  {String} str  The user-submitted string
 * @return {String} str  The sanitized string
 */
const sanitizeHTML = (data) => {
    if (data) {
        data = data.toString();
        return data.replace(/[^\w. ]/gi, function (c) {
            return '&#' + c.charCodeAt(0) + ';';
        });
    } else {
        return "";
    }
};

function showTable() {
    qrScanner.stop();

    document.getElementById("user").style.display = "none";
    document.getElementById("scanner").style.display = "none";
    document.getElementById("users").style.display = "block";
}

function showQR() {
    qrScanner.start();

    const camLS = localStorage.getItem("adminCam");
    if (camLS && typeof camLS !== "undefined") {
        qrScanner.setCamera(camLS);
    }

    document.getElementById("user").style.display = "none";
    document.getElementById("users").style.display = "none";
    document.getElementById("scanner").style.display = "block";
}

function showUser(userId) {
    const user = userDict[userId]

    // Header details
    document.getElementById("pfp").src = user.pfp;
    document.getElementById("name").innerText = user.name;
    document.getElementById("discord").innerText = user.username;

    // Statuses
    document.getElementById("statusColor").style.color = user.is_full_member ? "#51cd7f" : "#cf565f";

    document.getElementById("status").innerText = user.status;
    document.getElementById("did_pay_dues").innerText = user.did_pay_dues ? "✔️" : "❌";
    document.getElementById("ethics_form").innerText = (user.ethics_form.signtime && (Number.parseInt(user.ethics_form.signtime) !== -1)) ? (new Date(Number.parseInt(user.ethics_form.signtime))).toLocaleString() : "❌";
    document.getElementById("is_full_member").innerText = user.is_full_member ? "✔️" : "❌";
    document.getElementById("shirt_status").innerText = user.did_get_shirt ? "Claimed" : `Unclaimed: Size ${user.shirt_size}`

    let mentee_status = (user.mentee && user.mentee.time_in_cyber) ? "➖ Requested" : "❌";
    if (user.mentor_name) {
        mentee_status = "✔️ Assigned to " + user.mentor_name;
    }
    document.getElementById("mentee_status").innerHTML =  mentee_status;

    // Identifiers
    document.getElementById("id").innerText = user.id;
    document.getElementById("nid").innerText = user.nid;
    document.getElementById("ucfid").innerText = user.ucfid ? user.ucfid : "(unknown)";
    document.getElementById("email").innerText = user.email;
    document.getElementById("infra_email").innerText = user.infra_email ? user.infra_email : "Account Not Provisioned";
    document.getElementById("minecraft").innerText = user.minecraft ? user.minecraft : "Not Provided";
    document.getElementById("github").innerText = user.github ? user.github : "Not Provided";
    document.getElementById("phone_number").innerText = user.phone_number ? user.phone_number : "Not Provided";

    // Demography
    document.getElementById("class_standing").innerText = user.class_standing;
    document.getElementById("experience").innerText = user.experience;
    document.getElementById("attending").innerText = user.attending ? user.attending : "(none)";
    document.getElementById("curiosity").innerText = user.curiosity ? user.curiosity : "(none)";
    document.getElementById("major").innerText = user.major ? user.major : "(unknown)";
    document.getElementById("gender").innerText = user.gender ? user.gender : "(unknown)";
    document.getElementById("c3_interest").innerText = user.c3_interest ? "✔️" : "❌";
    document.getElementById("is_returning").innerText = user.is_returning ? "✔️" : "❌";
    document.getElementById("comments").innerText = user.comments ? user.comments : "(none)";

    document.getElementById("user_json").innerText = JSON.stringify(user, "\t", "\t")

    // Set buttons up
    document.getElementById("payDues").onclick = (evt) => {
        editUser({
            "id": user.id,
            "did_pay_dues": true
        });
        setTimeout(evt => {
            verifyUser(user.id);
        }, 2000);
    };
    document.getElementById("payDues").style.display = user.did_pay_dues ? "none" : "inline-block";

    document.getElementById("reverify").onclick = (evt) => {
        verifyUser(user.id);
    };
    document.getElementById("reverify").style.display = user.is_full_member ? "none" : "inline-block";

    document.getElementById("claimShirt").onclick = (evt) => {
        editUser({
            "id": user.id,
            "did_get_shirt": true
        })
    };
    document.getElementById("claimShirt").style.display = user.did_get_shirt ? "none" : "inline-block";

    document.getElementById("setAdmin").onclick = (evt) => {
        editUser({
            "id": user.id,
            "sudo": !user.sudo
        })
    };
    document.getElementById("adminLabel").innerText = user.sudo ? "Revoke Admin" : "Promote to Admin";

    document.getElementById("joinInfra").onclick = (evt) => {
        inviteToInfra(user.id);
    };
    document.getElementById("infraLabel").innerText = user.infra_email ? "Reset Infra Account" : "Invite to Infra";

    document.getElementById("assignMentor").onclick = (evt) => {
        let mentor_name = prompt("Please enter the mentor's name below:");
        editUser({
            "id": user.id,
            "mentor_name": mentor_name
        });
    };
    document.getElementById("assignMentor").style.display = (user.mentee && user.mentee.time_in_cyber) ? "inline-block" : "none";


    document.getElementById("sendMessage").onclick = (evt) => {
        const message = prompt("Please enter message to send to user:");
        sendDiscordDM(user.id, message);
    }

    // Set page visibilities
    document.getElementById("users").style.display = "none";
    document.getElementById("scanner").style.display = "none";
    document.getElementById("user").style.display = "block";
}

function editUser(payload) {
    const options = {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {
            "Content-Type": "application/json"
        }
    }
    const user_id = payload.id;
    fetch("/admin/get", options).then(data => {
        return data.json();
    }).then(data2 => {
        // Update user data.
        let member = data2.data;

        member.name = member.first_name + " " + member.surname;
        member.username = "@" + member.discord.username;
        member.pfp = member.discord.avatar;
        member.status = userStatusString(member);

        userDict[user_id] = member;
        showUser(user_id);
    })
}

function sendDiscordDM(user_id, message) {
    const payload = {
        "msg": message
    }
    const options = {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {
            "Content-Type": "application/json"
        }
    }
    fetch("/admin/message?member_id=" + user_id, options).then(data => {
        return data.json();
    }).then(data2 => {
        alert(data2.msg);
    })
}

function verifyUser(user_id) {
    fetch("/admin/refresh?member_id=" + user_id).then(data => {
        return data.json();
    }).then(data2 => {
        // Update user data.
        let member = data2.data;

        member.name = member.first_name + " " + member.surname;
        member.username = "@" + member.discord.username;
        member.pfp = member.discord.avatar;
        member.status = userStatusString(member);

        userDict[user_id] = member;
        showUser(user_id);
    })
}

function inviteToInfra(user_id) {
    fetch("/admin/infra?member_id=" + user_id).then(data => {
        return data.json();
    }).then(resp => {
        // Update user data.
        alert(`The user has been provisioned and a Discord message with credentials sent!

Username: ${resp.username}
Password: ${resp.password}`);

        userDict[user_id].infra_email = resp.username;
        showUser(user_id);
    })
}

function logoff() {
    document.cookie = 'token=; Max-Age=0; path=/; domain=' + location.hostname;
    window.location.href = "/logout";
}

function changeCamera() {
    QrScanner.listCameras().then(evt => {
        const cameras = evt;
        let camArray = [];
        let camString = "Please enter a camera number:";
        for (let i = 0; i < cameras.length; i++) {
            camString += `\n${i}: ${cameras[i].label}`;
            camArray.push(cameras[i].id);
        }
        let camSelect = prompt(camString);

        localStorage.setItem("adminCam", camArray[camSelect]);
        qrScanner.setCamera(camArray[camSelect]);
    });
}

function scannedCode(result) {
    // Enter load mode...
    qrScanner.stop();

    showUser(result.data);
}

function filter(showOnlyActiveUsers) {
    // showActiveUsers == true -> only active shown
    // showActiveUsers == false -> only inactive shown
    userList.filter((item) => {
        let activeOrInactive = item.values().is_full_member;
        if (!showOnlyActiveUsers) {
            activeOrInactive = !activeOrInactive
        }
        return activeOrInactive;
    });

    document.getElementById("activeFilter").innerText = showOnlyActiveUsers ? "Active" : "Inactive"
    document.getElementById("activeFilter").onclick = (evt) => {
        filter(!showOnlyActiveUsers);
    }
}

function mentorFilter(isMentorMode) {
    // isMentorMode == true -> show those in mentor program
    // isMentorMode == false -> show all
    userList.filter((item) => {
        let activeOrInactive = (item.values().mentee && item.values().mentee !== "Not Mentee");
        if (!isMentorMode) {
            activeOrInactive = true;
        }
        return activeOrInactive;
    });

    document.getElementById("menteeFilter").innerText = isMentorMode ? "Mentees" : "All Mentee"
    document.getElementById("menteeFilter").onclick = (evt) => {
        mentorFilter(!isMentorMode);
    }
}

window.onload = evt => {
    load();

    // Prep QR library
    const videoElem = document.querySelector("video");
    qrScanner = new QrScanner(
        videoElem,
        scannedCode,
        {
            maxScansPerSecond: 10,
            highlightScanRegion: true,
            returnDetailedScanResult: true
        },
    );

    // Default behavior
    document.getElementById("goBackBtn").onclick = (evt) => {
        showTable();
    }

    // Turn ON the QR Scanner mode.
    document.getElementById("scannerOn").onclick = (evt) => {
        showQR();

        document.getElementById("goBackBtn").onclick = (evt) => {
            showQR();
        }
    }

    document.getElementById("scannerOff").onclick = (evt) => {
        showTable();

        document.getElementById("goBackBtn").onclick = (evt) => {
            showTable();
        }
    }

    document.getElementById("changeCamera").onclick = (evt) => {
        changeCamera();
    }

    // Filter buttons
    document.getElementById("activeFilter").onclick = (evt) => {
        filter(true);
    }

    document.getElementById("menteeFilter").onclick = (evt) => {
        mentorFilter(true);
    }
}
