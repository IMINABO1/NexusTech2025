// Utility function to calculate distance between two coordinates
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3959; // Earth's radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Display flash messages
function showFlashMessage(message, type = 'success') {
    const flashContainer = document.createElement('div');
    flashContainer.className = `fixed top-4 right-4 p-4 rounded-lg ${
        type === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
    }`;
    flashContainer.textContent = message;
    document.body.appendChild(flashContainer);
    setTimeout(() => flashContainer.remove(), 3000);
}

// Form validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('border-red-500');
            const errorMessage = document.createElement('p');
            errorMessage.className = 'text-red-500 text-sm mt-1';
            errorMessage.textContent = 'This field is required';
            field.parentNode.appendChild(errorMessage);
        }
    });

    return isValid;
}

// Handle form submissions with AJAX
function handleFormSubmit(formElement, successCallback) {
    formElement.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!validateForm(formElement)) return;

        const formData = new FormData(formElement);
        try {
            const response = await fetch(formElement.action, {
                method: formElement.method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            if (data.success) {
                showFlashMessage(data.message);
                if (successCallback) successCallback(data);
            } else {
                showFlashMessage(data.message, 'error');
            }
        } catch (error) {
            showFlashMessage('An error occurred. Please try again.', 'error');
        }
    });
}

// Initialize all forms with AJAX submission
document.addEventListener('DOMContentLoaded', () => {
    const ajaxForms = document.querySelectorAll('form[data-ajax]');
    ajaxForms.forEach(form => {
        handleFormSubmit(form);
    });
});