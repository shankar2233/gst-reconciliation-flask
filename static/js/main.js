// Main JavaScript for GST Reconciliation Tool

document.addEventListener('DOMContentLoaded', function() {
    // File upload validation
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const tallyFile = document.getElementById('tally_file').files[0];
            const gstrFile = document.getElementById('gstr_file').files[0];
            
            if (!tallyFile || !gstrFile) {
                e.preventDefault();
                alert('Please select both files');
                return;
            }
            
            // Check file types
            const allowedTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                                'application/vnd.ms-excel'];
            
            if (!allowedTypes.includes(tallyFile.type) || !allowedTypes.includes(gstrFile.type)) {
                e.preventDefault();
                alert('Please select only Excel files (.xlsx or .xls)');
                return;
            }
            
            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            submitBtn.disabled = true;
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Table sorting functionality
    const tables = document.querySelectorAll('table');
    tables.forEach(function(table) {
        const headers = table.querySelectorAll('th');
        headers.forEach(function(header, index) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                sortTable(table, index);
            });
        });
    });
});

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const isNumeric = !isNaN(rows[0].cells[column].textContent);
    
    rows.sort(function(a, b) {
        const aVal = a.cells[column].textContent.trim();
        const bVal = b.cells[column].textContent.trim();
        
        if (isNumeric) {
            return parseFloat(aVal) - parseFloat(bVal);
        } else {
            return aVal.localeCompare(bVal);
        }
    });
    
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
}

// Progress bar animation
function animateProgressBar(element, targetWidth) {
    let width = 0;
    const interval = setInterval(function() {
        if (width >= targetWidth) {
            clearInterval(interval);
        } else {
            width += 2;
            element.style.width = width + '%';
        }
    }, 20);
}

// Initialize progress bars with animation
document.addEventListener('DOMContentLoaded', function() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(function(bar) {
        const targetWidth = parseFloat(bar.style.width);
        bar.style.width = '0%';
        setTimeout(function() {
            animateProgressBar(bar, targetWidth);
        }, 500);
    });
});
