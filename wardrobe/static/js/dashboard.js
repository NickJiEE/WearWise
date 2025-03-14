let temperatureChart;
// let humidityChart;
// let lightChart;

window.addEventListener("DOMContentLoaded", () => {
  window.PAGE_LOAD_TIME = new Date().toISOString();
  // Fetch and set user's default location for the weather forecast.
  fetch("/api/user")
    .then(response => response.json())
    .then(data => {
      if (data.location) {
        // Set global variable if needed
        window.USER_LOCATION = data.location;
        // Set the default value of the city input in the weather form
        const cityInput = document.getElementById("city");
        if (cityInput) {
          cityInput.value = data.location;
        }
      }
      // Optionally, you can also store the user ID if needed:
      if (data.user_id) {
        window.USER_ID = data.user_id;
      }

    })
    .catch(error => {
      console.error("Error fetching user location:", error);
    });
    
    // Load all charts on page load
    const customDateInputs = document.getElementById("customDateInputs");
        const dataRangeRadios = document.getElementsByName("dataRange");
        dataRangeRadios.forEach(radio => {
          radio.addEventListener("change", function() {
            if (this.value === "custom") {
              customDateInputs.style.display = "block";
            } else {
              customDateInputs.style.display = "none";
            }
          });
        });

    const dataRangeForm = document.getElementById("dataRangeForm");
    if (dataRangeForm) {
      dataRangeForm.addEventListener("submit", (event) => {
        event.preventDefault();
        loadAllCharts();
      });
    }
    startRealTimeUpdates();
});

function loadAllCharts() {
  const dataRange = document.querySelector('input[name="dataRange"]:checked').value;
  let startDateTime = null;
  let endDateTime = null;
  
  if (dataRange === "realTime") {
    // Use the page load time as the start date
    startDateTime = window.PAGE_LOAD_TIME;
  } else if (dataRange === "custom") {
    // Use custom values from the form
    const range = getDateRange();
    startDateTime = range.startDateTime;
    endDateTime = range.endDateTime;
  }

  fetchSensorData("temperature", startDateTime, endDateTime, window.SELECTED_DEVICE_ID)
  .then((tempData) => {
    renderChart("temperatureChart", tempData, "Temperature (°F)");
  });

  // Comment out humidity and light charts for now
  // fetchSensorData("humidity", startDateTime, endDateTime).then((humidityData) => {
  //   renderChart("humidityChart", humidityData, "Humidity");
  // });

  // fetchSensorData("light", startDateTime, endDateTime).then((lightData) => {
  //   renderChart("lightChart", lightData, "Light");
  // });
}

function getDateRange() {
  const startInput = document.getElementById("start");
  const endInput = document.getElementById("end");

  const startDateTime = startInput ? startInput.value : null;
  const endDateTime = endInput ? endInput.value : null;

  return { 
    startDateTime: startDateTime || null, 
    endDateTime: endDateTime || null 
  };
}

async function fetchSensorData(sensorType, startDateTime, endDateTime, deviceId = null) {
  let url = `/api/${sensorType}`;
  let params = [];

  params.push("order-by=timestamp");

  if (startDateTime) {
    params.push(`start-date=${encodeURIComponent(startDateTime)}`);
  }
  if (endDateTime) {
    params.push(`end-date=${encodeURIComponent(endDateTime)}`);
  }
  // Optional device filtering
  if (deviceId) {
    params.push(`device_id=${encodeURIComponent(deviceId)}`);
  }

  if (params.length > 0) {
    url += "?" + params.join("&");
  }

  const response = await fetch(url);
  const data = await response.json();
  data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  return data;
}

function renderChart(canvasId, dataArr, labelName) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");
  const parent = canvas.parentNode;

  // Remove any previous "no data" message if it exists
  const existingMsg = parent.querySelector('.no-data-message');
  if (existingMsg) {
    existingMsg.remove();
  }

  // If no data available, clear canvas and display a message
  if (dataArr.length === 0) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (window[canvasId + "Instance"]) {
      window[canvasId + "Instance"].destroy();
    }
    const messageDiv = document.createElement("div");
    messageDiv.className = "no-data-message";
    messageDiv.style.textAlign = "center";
    messageDiv.style.padding = "20px";
    messageDiv.textContent = "No data available for the selected period.";
    parent.appendChild(messageDiv);
    return;
  }

  // Group data by device_id
  const groupedData = {};
  dataArr.forEach(row => {
    const dev = row.device_id || "unknown";
    if (!groupedData[dev]) {
      groupedData[dev] = [];
    }
    groupedData[dev].push(row);
  });

  // Create a color palette for multiple datasets
  const colors = [
    "rgb(145, 192, 75)",
    "rgb(75, 192, 192)",
    "rgb(192, 75, 145)",
    "rgb(192, 145, 75)",
    "rgb(75, 145, 192)",
    "rgb(145, 75, 192)"
  ];

  // Create datasets for each device
  const datasets = [];
  let colorIndex = 0;
  for (const deviceId in groupedData) {
    // Sort each device's data by timestamp
    const deviceData = groupedData[deviceId].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    datasets.push({
      label: `Device ID: ${deviceId}`,
      data: deviceData.map(row => row.temp),
      borderColor: colors[colorIndex % colors.length],
      fill: false,
      tension: 0.1,
    });
    colorIndex++;
  }

  let labels = [];
  const firstKey = Object.keys(groupedData)[0];
  if (firstKey) {
    labels = groupedData[firstKey].map(row => row.timestamp);
  }

  // Destroy existing chart if exists
  if (window[canvasId + "Instance"]) {
    window[canvasId + "Instance"].destroy();
  }

  // Create the chart with multiple datasets
  window[canvasId + "Instance"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets,
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            // Optionally, include device id in the tooltip
            label: function(context) {
              const deviceId = context.dataset.label;
              const value = context.parsed.y;
              return `${deviceId}: ${value} ${context.dataset.unit || ""}`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Timestamp",
          },
        },
        y: {
          title: {
            display: true,
            text: labelName,
          },
        },
      },
    },
  });
}

function startRealTimeUpdates() {
  setInterval(async () => {
    const { startDateTime, endDateTime } = getDateRange(); 
    const tempData = await fetchSensorData("temperature", startDateTime, endDateTime, window.SELECTED_DEVICE_ID);
    
    if (window.temperatureChartInstance) {
      // Update labels and data
      window.temperatureChartInstance.data.labels = tempData.map(row => row.timestamp);
      window.temperatureChartInstance.data.datasets[0].data = tempData.map(row => row.temp);
      window.temperatureChartInstance.update();
    } else {
      // Create a new chart instance
      renderChart("temperatureChart", tempData, "Temperature (°F)");
    }
  }, 5000);
}

document.getElementById("deviceSelector").addEventListener("change", function() {
  window.SELECTED_DEVICE_ID = this.value || null;
  loadAllCharts(); // Reload charts based on selected device
});