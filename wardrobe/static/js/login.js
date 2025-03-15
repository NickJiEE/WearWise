document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const totpForm = document.getElementById('totp-form');
    const userIdInput = document.getElementById('user-id-input');
    const loginError = document.getElementById('login-error');
    const totpError = document.getElementById('totp-error');
    const backButton = document.getElementById('back-button');
    
    // Handle login form submission
    loginForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        loginError.style.display = 'none';
        
        const formData = new FormData(loginForm);
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                body: formData
            });
            
            // Check response type
            const contentType = response.headers.get('content-type');
            
            if (!response.ok) {
                const errorData = await response.json();
                loginError.textContent = errorData.detail || 'Login failed';
                loginError.style.display = 'block';
                return;
            }
            
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                
                // If TOTP verification is required
                if (data.requires_totp) {
                    loginForm.style.display = 'none';
                    totpForm.style.display = 'block';
                    userIdInput.value = data.user_id;
                    
                    // Focus on the TOTP input field
                    setTimeout(() => {
                        totpForm.querySelector('input[name="totp_code"]').focus();
                    }, 100);
                } else {
                    // Redirect to dashboard
                    window.location.href = '/dashboard';
                }
            } else {
                // Handle redirect (FastAPI might have already done it)
                window.location.href = '/dashboard';
            }
        } catch (error) {
            console.error('Login error:', error);
            loginError.textContent = 'An error occurred during login. Please try again.';
            loginError.style.display = 'block';
        }
    });
    
    // Handle TOTP form submission
    totpForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        totpError.style.display = 'none';
        
        const formData = new FormData(totpForm);
        
        try {
            const response = await fetch('/verify-totp', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                totpError.textContent = errorData.detail || 'Verification failed';
                totpError.style.display = 'block';
                return;
            }
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            console.error('TOTP verification error:', error);
            totpError.textContent = 'An error occurred during verification. Please try again.';
            totpError.style.display = 'block';
        }
    });
    
    // Back button functionality
    backButton.addEventListener('click', function(event) {
        event.preventDefault();
        totpForm.style.display = 'none';
        loginForm.style.display = 'block';
    });
});