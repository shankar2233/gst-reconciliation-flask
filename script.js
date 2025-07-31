// Enhanced JavaScript with animations and interactions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize animations
    initializeAnimations();
    
    // File upload handling
    setupFileUpload();
    
    // Progress animations
    setupProgressAnimations();
    
    // Table interactions
    setupTableInteractions();
    
    // Auto-dismiss alerts
    setupAlertDismissal();
});

function initializeAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    // Observe all cards and sections
    document.querySelectorAll('.card, .alert, .table-responsive').forEach(el => {
        observer.observe(el);
    });

    // Stagger animations for status cards
    const statusCards = document.querySelectorAll('.status-card');
    statusCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

function setupFileUpload() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('gst_file');
    const uploadArea = document.querySelector('.file-upload-area');

    if (uploadForm && fileInput) {
        // Create drag and drop area
        createDragDropArea();
        
        // Form submission with loading state
        uploadForm.addEventListener('submit', function(e) {
            const file = fileInput.files[0];
            
            if (!file) {
                e.preventDefault();
                showNotification('Please select a file', 'warning');
                return;
            }
            
            // Check file type
            const allowedTypes = [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                'application/vnd.ms-excel'
            ];
            
            if (!allowedTypes.includes(file.type)) {
                e.preventDefault();
                showNotification('Please select only Excel files (.xlsx or .xls)', 'error');
                return;
            }
            
            // Show loading state
            showLoadingState();
        });
    }
}

function createDragDropArea() {
    const fileInput = document.getElementById('gst_file');
    const uploadArea = document.querySelector('.card-body');
    
    if (fileInput && uploadArea) {
        // Add drag and drop styling
        uploadArea.classList.add('file-upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            uploadArea.classList.add('dragover');
            uploadArea.style.transform = 'scale(1.02)';
        }

        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
            uploadArea.style.transform = 'scale(1)';
        }

        uploadArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                showNotification(`File "${files[0].name}" selected successfully!`, 'success');
                animateFileSelection();
            }
        }
    }
}

function animateFileSelection() {
    const fileInput = document.getElementById('gst_file');
    const submitBtn = document.querySelector('button[type="submit"]');
    
    if (fileInput && submitBtn) {
        // Animate submit button
        submitBtn.classList.add('bounce-in');
        submitBtn.style.animation = 'bounceIn 0.6s ease-out';
        
        setTimeout(() => {
            submitBtn.style.animation = '';
        }, 600);
    }
}

function showLoadingState() {
    const submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<div class="loading-spinner"></div> Processing...';
        submitBtn.disabled = true;
        
        // Add progress bar
        createProgressBar();
    }
}

function createProgressBar() {
    const form = document.getElementById('uploadForm');
    if (form) {
        const progressContainer = document.createElement('div');
        progressContainer.className = 'mt-3';
        progressContainer.innerHTML = `
            <div class="progress">
                <div class="progress-bar progress-bar-animated" role="progressbar" style="width: 0%">
                    <span class="sr-only">Processing...</span>
                </div>
            </div>
            <small class="text-muted mt-1 d-block">Processing your file...</small>
        `;
        
        form.appendChild(progressContainer);
        
        // Animate progress
        const progressBar = progressContainer.querySelector('.progress-bar');
        setTimeout(() => {
            progressBar.style.width = '30%';
        }, 500);
        setTimeout(() => {
            progressBar.style.width = '60%';
        }, 1500);
        setTimeout(() => {
            progressBar.style.width = '90%';
        }, 2500);
    }
}

function setupProgressAnimations() {
    // Animate progress bars on page load
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach((bar, index) => {
        const targetWidth = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.transition = 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)';
            bar.style.width = targetWidth;
            
            // Add counter animation for text content
            animateCounter(bar, targetWidth);
        }, index * 200 + 500);
    });
}

function animateCounter(element, targetPercent) {
    const target = parseInt(targetPercent);
    const duration = 1500;
    const increment = target / (duration / 16);
    let current = 0;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        
        // Update any counter text in nearby elements
        const parentCard = element.closest('.card');
        if (parentCard) {
            const counterElement = parentCard.querySelector('h4, .display-4');
            if (counterElement && !isNaN(parseInt(counterElement.textContent))) {
                counterElement.textContent = Math.round(current);
            }
        }
    }, 16);
}

function setupTableInteractions() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Add hover effects to rows
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, index) => {
            row.style.animationDelay = `${index * 0.05}s`;
            row.classList.add('fade-in');
            
            row.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.01) translateX(5px)';
                this.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.1)';
            });
            
            row.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1) translateX(0)';
                this.style.boxShadow = 'none';
            });
        });
        
        // Add sorting functionality
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            if (header.textContent.trim()) {
                header.style.cursor = 'pointer';
                header.style.userSelect = 'none';
                
                // Add sort icon
                const sortIcon = document.createElement('i');
                sortIcon.className = 'fas fa-sort ms-2';
                header.appendChild(sortIcon);
                
                header.addEventListener('click', function() {
                    sortTable(table, index);
                    
                    // Animate sort icon
                    sortIcon.style.transform = 'rotate(180deg)';
                    setTimeout(() => {
                        sortIcon.style.transform = 'rotate(0deg)';
                    }, 200);
                });
            }
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const isNumeric = !isNaN(parseFloat(rows[0]?.cells[column]?.textContent?.trim()));
    
    rows.sort((a, b) => {
        const aVal = a.cells[column]?.textContent?.trim() || '';
        const bVal = b.cells[column]?.textContent?.trim() || '';
        
        if (isNumeric) {
            return parseFloat(aVal) - parseFloat(bVal);
        } else {
            return aVal.localeCompare(bVal);
        }
    });
    
    // Animate row reordering
    rows.forEach((row, index) => {
        row.style.transform = 'translateX(-100%)';
        row.style.opacity = '0';
        
        setTimeout(() => {
            tbody.appendChild(row);
            row.style.transition = 'all 0.3s ease';
            row.style.transform = 'translateX(0)';
            row.style.opacity = '1';
        }, index * 50);
    });
}

function setupAlertDismissal() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.transform = 'translateX(100%)';
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
}

function showNotification(message, type = 'info') {
    const alertContainer = document.querySelector('.container.mt-3') || document.querySelector('.container');
    if (alertContainer) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show slide-in-right`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
        
        // Auto-dismiss
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.style.transform = 'translateX(100%)';
                alertDiv.style.opacity = '0';
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 300);
            }
        }, 4000);
    }
}

// Tab animations
document.addEventListener('shown.bs.tab', function(e) {
    const tabPane = document.querySelector(e.target.getAttribute('data-bs-target'));
    if (tabPane) {
        tabPane.style.opacity = '0';
        tabPane.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            tabPane.style.transition = 'all 0.3s ease';
            tabPane.style.opacity = '1';
            tabPane.style.transform = 'translateY(0)';
        }, 50);
    }
});

// Smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add ripple effect to buttons
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// Add ripple effect CSS
const rippleCSS = `
.btn {
    position: relative;
    overflow: hidden;
}

.ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.4);
    transform: scale(0);
    animation: ripple-animation 0.6s linear;
    pointer-events: none;
}

@keyframes ripple-animation {
    to {
        transform: scale(4);
        opacity: 0;
    }
}
`;

// Inject ripple CSS
const style = document.createElement('style');
style.textContent = rippleCSS;
document.head.appendChild(style);
