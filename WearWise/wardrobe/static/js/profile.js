document.addEventListener('DOMContentLoaded', function() {
    const devicesList = document.getElementById('devicesList');
    const deviceInput = document.getElementById('deviceInput');
    const deviceNameInput = document.getElementById('deviceNameInput');
    const addDeviceButton = document.getElementById('addDevice');
    const deleteDeviceButton = document.getElementById('deleteDevice');
    const scanQrCodeButton = document.getElementById('scanQrCode');
    const scannerModal = document.getElementById('scannerModal');
    const closeModalButton = document.getElementById('closeModal');
    
    // TOTP related elements
    const totpStatus = document.getElementById('totp-status');
    const totpSetupBtn = document.getElementById('totp-setup-btn');
    
    let selectedDeviceId = null;
    let html5QrCode = null;

    // Function to fetch TOTP status
    function fetchTOTPStatus() {
        fetch('/api/totp/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch TOTP status');
                }
                return response.json();
            })
            .then(data => {
                if (data.totp_enabled) {
                    totpStatus.textContent = 'Enabled';
                    totpStatus.className = 'status-indicator status-enabled';
                    totpSetupBtn.textContent = 'Manage 2FA';
                } else {
                    totpStatus.textContent = 'Not Enabled';
                    totpStatus.className = 'status-indicator status-disabled';
                    totpSetupBtn.textContent = 'Set up 2FA';
                }
            })
            .catch(error => {
                console.error('Error fetching TOTP status:', error);
                totpStatus.textContent = 'Unknown';
                totpStatus.className = 'status-indicator';
            });
    }

    // Function to fetch and display the list of devices
    function fetchDevices() {
        fetch('/api/devices')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch devices');
                }
                return response.json();
            })
            .then(devices => {
                devicesList.innerHTML = ''; // Clear the current list
                
                if (devices.length === 0) {
                    const emptyMessage = document.createElement('li');
                    emptyMessage.textContent = 'No devices added yet.';
                    emptyMessage.className = 'empty-list';
                    devicesList.appendChild(emptyMessage);
                    
                    // Disable delete button when no devices exist
                    deleteDeviceButton.disabled = true;
                } else {
                    devices.forEach(device => {
                        const li = document.createElement('li');
                        li.textContent = device.name ? `${device.device_id} (${device.name})` : device.device_id;
                        
                        // Store the device_id as a data attribute
                        li.dataset.deviceId = device.device_id;
                        
                        // Add click event to make the item selectable
                        li.addEventListener('click', function() {
                            // Clear previous selection
                            document.querySelectorAll('#devicesList li').forEach(item => {
                                item.classList.remove('selected');
                            });
                            
                            // Select this item
                            this.classList.add('selected');
                            selectedDeviceId = this.dataset.deviceId;
                            
                            // Enable delete button
                            deleteDeviceButton.disabled = false;
                        });
                        
                        devicesList.appendChild(li);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching devices:', error);
                devicesList.innerHTML = '<li class="empty-list">Error loading devices. Please refresh the page.</li>';
            });
    }

    // Function to add a device
    function addDevice(deviceId, deviceName) {
        fetch('/api/devices/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                device_id: deviceId,
                name: deviceName || null
            }),
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400) {
                    return response.json().then(data => {
                        throw new Error(data.detail || 'Failed to add device');
                    });
                }
                throw new Error('Failed to add device');
            }
            return response.json();
        })
        .then(data => {
            fetchDevices(); // Refresh the list
            deviceInput.value = ''; // Clear the input field
            deviceNameInput.value = ''; // Clear the name input field
            alert('Device added successfully!');
        })
        .catch(error => {
            alert(error.message);
            console.error('Error adding device:', error);
        });
    }

    // Function to delete a device
    function deleteDevice(deviceId) {
        fetch('/api/devices/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ device_id: deviceId }),
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    return response.json().then(data => {
                        throw new Error(data.detail || 'Device not found');
                    });
                }
                throw new Error('Failed to delete device');
            }
            return response.json();
        })
        .then(data => {
            // Reset selection state
            selectedDeviceId = null;
            deleteDeviceButton.disabled = true;
            
            fetchDevices(); // Refresh the list
            alert('Device deleted successfully!');
        })
        .catch(error => {
            alert(error.message);
            console.error('Error deleting device:', error);
        });
    }

    // Event listener for the ADD DEVICE button
    addDeviceButton.addEventListener('click', function() {
        const deviceId = deviceInput.value.trim();
        const deviceName = deviceNameInput.value.trim();
        
        if (deviceId) {
            addDevice(deviceId, deviceName);
        } else {
            alert('Please enter a device ID.');
        }
    });

    // Event listener for the DELETE DEVICE button
    deleteDeviceButton.addEventListener('click', function() {
        if (selectedDeviceId) {
            if (confirm(`Are you sure you want to delete the selected device: ${selectedDeviceId}?`)) {
                deleteDevice(selectedDeviceId);
            }
        } else {
            alert('Please select a device to delete.');
        }
    });

    // QR Code Scanner Functionality
    function initQrScanner() {
        const qrCodeSuccessCallback = (decodedText) => {
            // Stop scanning after successful scan
            stopQrScanner();
            
            // Close the modal
            scannerModal.style.display = 'none';
            
            // Update the device input field with the scanned code
            deviceInput.value = decodedText;
            
            // Focus on the name input for better UX
            deviceNameInput.focus();
        };

        const config = { fps: 10, qrbox: { width: 250, height: 250 } };
        
        // Initialize the scanner
        html5QrCode = new Html5Qrcode("qr-reader");
        
        html5QrCode.start(
            { facingMode: "environment" }, // Use the back camera
            config,
            qrCodeSuccessCallback
        ).catch(error => {
            console.error('Error starting QR scanner:', error);
            alert('Could not start the camera. Please check your camera permissions.');
        });
    }

    function stopQrScanner() {
        if (html5QrCode && html5QrCode.isScanning) {
            html5QrCode.stop().catch(error => {
                console.error('Error stopping QR scanner:', error);
            });
        }
    }

    // Event listener for the Scan QR Code button
    scanQrCodeButton.addEventListener('click', function() {
        scannerModal.style.display = 'block';
        initQrScanner();
    });

    // Event listener for the Close Modal button
    closeModalButton.addEventListener('click', function() {
        stopQrScanner();
        scannerModal.style.display = 'none';
    });

    // Also close the modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === scannerModal) {
            stopQrScanner();
            scannerModal.style.display = 'none';
        }
    });

    // Initial fetch to populate the devices list when the page loads
    fetchDevices();
    
    // Initial fetch of TOTP status
    fetchTOTPStatus();
});