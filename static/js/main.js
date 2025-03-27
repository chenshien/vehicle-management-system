// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 设置所有提示框的自动关闭时间
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000); // 5秒后自动关闭
    });
    
    // 初始化所有工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 当申请详情页面中有表单时，添加动态表单验证
    var applicationForms = document.querySelectorAll('.application-form');
    if (applicationForms.length > 0) {
        applicationForms.forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // 当有日期选择器时，初始化
    var datePickers = document.querySelectorAll('.datepicker');
    if (datePickers.length > 0 && typeof flatpickr !== 'undefined') {
        datePickers.forEach(function(picker) {
            flatpickr(picker, {
                dateFormat: "Y-m-d",
                locale: "zh"
            });
        });
    }
    
    // 当有时间选择器时，初始化
    var timePickers = document.querySelectorAll('.timepicker');
    if (timePickers.length > 0 && typeof flatpickr !== 'undefined') {
        timePickers.forEach(function(picker) {
            flatpickr(picker, {
                enableTime: true,
                noCalendar: true,
                dateFormat: "H:i",
                locale: "zh"
            });
        });
    }
    
    // 当有日期时间选择器时，初始化
    var dateTimePickers = document.querySelectorAll('.datetimepicker');
    if (dateTimePickers.length > 0 && typeof flatpickr !== 'undefined') {
        dateTimePickers.forEach(function(picker) {
            flatpickr(picker, {
                enableTime: true,
                dateFormat: "Y-m-d H:i",
                locale: "zh"
            });
        });
    }
    
    // 当有文件上传框时，添加文件名显示功能
    var fileInputs = document.querySelectorAll('.form-control-file');
    if (fileInputs.length > 0) {
        fileInputs.forEach(function(input) {
            input.addEventListener('change', function(e) {
                var fileName = e.target.files[0].name;
                var label = input.nextElementSibling;
                if (label && label.classList.contains('custom-file-label')) {
                    label.textContent = fileName;
                }
            });
        });
    }
}); 