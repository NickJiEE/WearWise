document.addEventListener('DOMContentLoaded', async function() {
  const setupSection = document.getElementById('setup-section');
  const disableSection = document.getElementById('disable-section');
  const setupMessage = document.getElementById('setup-message');
  const secretInput = document.getElementById('secret-input');
  const secretKeyDisplay = document.getElementById('secret-key');
  const qrCodeImg = document.getElementById('qr-code');
  const enableForm = document.getElementById('enable-totp-form');
  const disableForm = document.getElementById('disable-totp-form');
  
  // Function to show message
  function showMessage(message, isSuccess) {
    setupMessage.textContent = message;
    setupMessage.className = isSuccess 
      ? 'setup-message setup-success' 
      : 'setup-message setup-error';
    setupMessage.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      setupMessage.style.display = 'none';
    }, 5000);
  }
  
  // Check current TOTP status
  try {
    const response = await fetch('/api/totp/status');
    const data = await response.json();
    
    if (data.totp_enabled) {
      // TOTP is already enabled, show disable section
      setupSection.style.display = 'none';
      disableSection.style.display = 'block';
    } else {
      // TOTP is not enabled, setup QR code and secret
      const setupResponse = await fetch('/api/totp/setup');
      const setupData = await setupResponse.json();
      
      // Display QR code
      qrCodeImg.src = setupData.qr_code;
      
      // Display and store secret
      secretKeyDisplay.textContent = setupData.secret;
      secretInput.value = setupData.secret;
    }
  } catch (error) {
    console.error('Error fetching TOTP status:', error);
    showMessage('Failed to load TOTP setup. Please try again later.', false);
  }
  
  // Handle enable TOTP form submission
  enableForm.addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const formData = new FormData(enableForm);
    
    try {
      const response = await fetch('/api/totp/enable', {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        showMessage('Two-factor authentication successfully enabled!', true);
        
        // Redirect to profile page after 2 seconds
        setTimeout(() => {
          window.location.href = '/profile';
        }, 2000);
      } else {
        const errorData = await response.json();
        showMessage('Error: ' + (errorData.detail || 'Failed to enable two-factor authentication'), false);
      }
    } catch (error) {
      console.error('TOTP enable error:', error);
      showMessage('Failed to enable two-factor authentication. Please try again.', false);
    }
  });
  
  // Handle disable TOTP form submission
  disableForm.addEventListener('submit', async function(event) {
    event.preventDefault();
    
    if (!confirm('Are you sure you want to disable two-factor authentication? This will reduce the security of your account.')) {
      return;
    }
    
    const formData = new FormData(disableForm);
    
    try {
      const response = await fetch('/api/totp/disable', {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        showMessage('Two-factor authentication successfully disabled.', true);
        
        // Redirect to profile page after 2 seconds
        setTimeout(() => {
          window.location.href = '/profile';
        }, 2000);
      } else {
        const errorData = await response.json();
        showMessage('Error: ' + (errorData.detail || 'Failed to disable two-factor authentication'), false);
      }
    } catch (error) {
      console.error('TOTP disable error:', error);
      showMessage('Failed to disable two-factor authentication. Please try again.', false);
    }
  });
});