// Get the file input element
const fileInput = document.getElementById('csvFile');
let csvData; 

// Event listener for when a file is selected
fileInput.addEventListener('change', handleFileSelect);

let userDict = {};
let results = [];
let csvResults;
let notFound = [];

window.onload = evt => {
    load();
}

function load(){
    let members = [];
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

            members.push(userEntry);

            member.name = member.first_name + " " + member.surname;
            member.username = "@" + member.discord.username;
            member.pfp = member.discord.avatar;
            member.status = userStatus;
            userDict[sickoModeSanitize(member.id)] = member;
        }
   
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


// Function to handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    // Event listener for when the file is loaded
    reader.addEventListener('load', function (event) {
        csvData = event.target.result; // Assign the loaded file data to csvData
        handleFileLoad(event); // Call the handleFileLoad function
    });

    // Read the file as text
    reader.readAsText(file);
}

// Function to handle file load
function handleFileLoad(event) {
  const csvData = event.target.result;
  const lines = csvData.split('\n');
  const columnTitles = lines[0].split(',');

  // Get the dropdown element
  const dropdown = document.getElementById('columnDropdown');

  // Clear existing options
  dropdown.innerHTML = '';

  // Create options for each column title
  columnTitles.forEach((title) => {
    const option = document.createElement('option');
    option.value = title;
    option.textContent = title;
    dropdown.appendChild(option);
  });
}


function processData() {
    var e = document.getElementById("columnDropdown");
    var title = e.value;
    var member_ids = getColumnByTitle(csvData, title);

    csvResults=csvData.split(/\r?\n/)
    // Strip double quotes from member_ids array
    member_ids = member_ids.map((id) => id.replace(/"/g, ''));
    for (let i = 0; i < member_ids.length; i++) {
        const memberId = member_ids[i];
        if (userDict[memberId] !== undefined) {
            const userDist = userDict[memberId];
            // Add results to results
            const memberStatus = userStatusString(userDist);
            csvResults[i+1] = `${csvResults[i + 1]}, ${memberStatus}`
            results.push(userDist);
            
        }
        else{
            csvResults[i+1] = `${csvResults[i + 1]}, Not Found`
            notFound.push(csvResults[i+1])
        }
    }
    createTable();
}
function createTable(){
// Create a table
var table = document.createElement('table');

// Create table header
var thead = document.createElement('thead');
var headerRow = document.createElement('tr');
['Member ID', 'Name', 'Email', 'Discord', 'Status'].forEach(headerText => {
    var th = document.createElement('th');
    th.textContent = headerText;
    headerRow.appendChild(th);
});
thead.appendChild(headerRow);
table.appendChild(thead);

// Create table body
var tbody = document.createElement('tbody');
results.forEach(user => {
    var row = document.createElement('tr');
    ['id', 'name', 'email', 'discord.username', 'status'].forEach(key => {
        var cell = document.createElement('td');
        var value = user;
        var keys = key.split('.');
        for (var i = 0; i < keys.length; i++) {
            value = value[keys[i]];
        }
        if (keys.includes('email')) {
            cell.classList.add('email');
        }
        if (keys.includes('id')) {
            cell.classList.add('id-truncate');
            cell.title = value;
        }
        cell.textContent = value;
        row.appendChild(cell);
    });
    tbody.appendChild(row);
});
table.appendChild(tbody);
// Append the table to the body (or any other container element)
var container = document.getElementById('userTable');
container.appendChild(table);

// Create table for notFound data
var notFoundTable = document.createElement('table');
// Create table header
var notFoundThead = document.createElement('thead');
notFoundTable.appendChild(notFoundThead);
// Create table body
var notFoundTbody = document.createElement('tbody');
notFound.forEach(data => {
    var row = document.createElement('tr');
    var csvDataCell = document.createElement('td');
    var statusCell = document.createElement('td');
    data.split(',').forEach(cellData => {
        var cell = document.createElement('td');
        cell.textContent = cellData;
        row.appendChild(cell);
    });
    notFoundTbody.appendChild(row);
});
notFoundTable.appendChild(notFoundTbody);

// Append the notFound table to the body (or any other container element)
var notFoundContainer = document.getElementById('notFoundTable');
notFoundContainer.appendChild(notFoundTable);

document.getElementById("results").style.display = "block";

}

function getColumnByTitle(csvData, title) {
    const lines = csvData.split('\n');
    const columnTitles = lines[0].split(',');
    const columnIndex = columnTitles.indexOf(title);
    const columnData = [];
    
    for (let i = 1; i < lines.length; i++) {
        const rowData = lines[i].split(',');
        if (rowData.length > columnIndex) {
            columnData.push(rowData[columnIndex]);
        }
    }
    
    return columnData;
}


function downloadCSV() {
    const csvContent = "data:text/csv;charset=utf-8," + csvResults.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "results.csv");
    document.body.appendChild(link);
    link.click();
}
