// List of cloth types in alphabetical order
const clothTypes = [
  "Acessories",
  "Cap",
  "Casual",
  "Coat",
  "Dress",
  "Hat",
  "Jacket",
  "Jeans",
  "Pajamas",
  "Sandal",
  "Shirt",
  "Shoes",
  "Shorts",
  "Socks",
  "Sportswear",
  "Suits",
  "Sweatpants",
  "T-shirt",
  "Underwear"
];

let USER_ID = null;

fetch("/api/user")
  .then(response => response.json())
  .then(data => {
    USER_ID = data.user_id;
    // console.log("User ID fetched:", USER_ID);
  })
  .catch(error => {
    console.error("Failed to fetch user ID:", error);
});
  
// Helper to create a modal overlay with a form container
function createModal() {
  const modal = document.createElement("div");
  modal.className = "modal-overlay";
  Object.assign(modal.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000
  });
  return modal;
}

// ADD CLOTH
function addCloth() {
  const modal = createModal();
  const form = document.createElement("div");
  Object.assign(form.style, {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "5px",
    minWidth: "300px"
  });

  // Cloth name input
  const nameLabel = document.createElement("label");
  nameLabel.textContent = "Cloth Name:";
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.style.display = "block";
  nameInput.style.marginBottom = "10px";

  // Cloth type select
  const typeLabel = document.createElement("label");
  typeLabel.textContent = "Cloth Type:";
  const typeSelect = document.createElement("select");
  typeSelect.style.display = "block";
  typeSelect.style.marginBottom = "10px";
  clothTypes.forEach(type => {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    typeSelect.appendChild(option);
  });

  // Submit and Cancel buttons
  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Submit";
  submitBtn.style.marginRight = "10px";
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";

  form.appendChild(nameLabel);
  form.appendChild(nameInput);
  form.appendChild(typeLabel);
  form.appendChild(typeSelect);
  form.appendChild(submitBtn);
  form.appendChild(cancelBtn);
  modal.appendChild(form);
  document.body.appendChild(modal);

  submitBtn.addEventListener("click", async () => {
    if (USER_ID === null) {
      try {
          const response = await fetch("/api/user");
          if (!response.ok) throw new Error("Failed to fetch user ID");
          const data = await response.json();
          USER_ID = data.user_id;
          // console.log("Fetched user ID inside addCloth:", USER_ID);
      } catch (error) {
          console.error("Error fetching user ID:", error);
          alert("Error fetching user ID. Please try again.");
          return;
      }
    }

    const clothName = nameInput.value.trim();
    const clothType = typeSelect.value;
    if (clothName === "") {
      alert("Please enter a cloth name.");
      return;
    }
    
    // console.log("Sending data:", JSON.stringify({ name: clothName, cloth_type: clothType, user_id: USER_ID }));

    fetch("/api/closet/add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ name: clothName, cloth_type: clothType, user_id: USER_ID })
    })
    .then(response => {
      if (response.ok) {
        return response.json();
      } else {
        throw new Error("Failed to add cloth.");
      }
    })
    .then(data => {
      // Update the UI with the new cloth
      const li = document.createElement("li");
      li.textContent = `${data.name} (${data.cloth_type})`;
      li.setAttribute("data-id", data.id);
      document.getElementById("clothesList").appendChild(li);
      document.body.removeChild(modal);
    })
    .catch(error => {
      console.error("Error:", error);
      alert("Error adding cloth.");
    });
  });

  cancelBtn.addEventListener("click", () => {
    document.body.removeChild(modal);
  });
}

// REMOVE CLOTH
function removeCloth() {
  const clothesList = document.getElementById("clothesList");
  const items = clothesList.getElementsByTagName("li");
  if (items.length === 0) {
    alert("No clothes available to remove.");
    return;
  }
  const modal = createModal();
  const form = document.createElement("div");
  Object.assign(form.style, {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "5px",
    minWidth: "300px"
  });

  const selectLabel = document.createElement("label");
  selectLabel.textContent = "Select Cloth to Remove:";
  const clothSelect = document.createElement("select");
  clothSelect.style.display = "block";
  clothSelect.style.marginBottom = "10px";

  // Populate select with current clothes
  for (let i = 0; i < items.length; i++) {
    const option = document.createElement("option");
    option.value = i; // using index as identifier, will map to cloth id in your data
    option.textContent = items[i].textContent;
    clothSelect.appendChild(option);
  }

  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.style.marginRight = "10px";
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";

  form.appendChild(selectLabel);
  form.appendChild(clothSelect);
  form.appendChild(confirmBtn);
  form.appendChild(cancelBtn);
  modal.appendChild(form);
  document.body.appendChild(modal);

  confirmBtn.addEventListener("click", async () => {
    const index = clothSelect.value;
    const clothId = items[index].getAttribute("data-id");
    if (!clothId) {
      alert("Invalid cloth selected.");
      return;
    }

    try {
      const response = await fetch("/api/closet/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(parseInt(clothId))
      });

      if (!response.ok) {
        throw new Error("Failed to delete cloth");
      }

      const result = await response.json();
      // console.log("Deleted cloth:", result);

      // Remove the item from the DOM
      clothesList.removeChild(items[index]);
      document.body.removeChild(modal);
    } catch (error) {
      console.error("Error deleting cloth:", error);
      alert("Error deleting cloth.");
    }
  });

  cancelBtn.addEventListener("click", () => {
    document.body.removeChild(modal);
  });
}

// UPDATE CLOTH
function updateCloth() {
  const clothesList = document.getElementById("clothesList");
  const items = clothesList.getElementsByTagName("li");
  if (items.length === 0) {
    alert("No clothes available to update.");
    return;
  }

  const modal = createModal();
  const form = document.createElement("div");
  Object.assign(form.style, {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "5px",
    minWidth: "300px"
  });

  const selectLabel = document.createElement("label");
  selectLabel.textContent = "Select Cloth to Update:";
  const clothSelect = document.createElement("select");
  clothSelect.style.display = "block";
  clothSelect.style.marginBottom = "10px";

  // Populate select with current clothes
  for (let i = 0; i < items.length; i++) {
    const option = document.createElement("option");
    option.value = items[i].getAttribute("data-id");  // Use cloth ID for updating
    option.textContent = items[i].textContent;
    clothSelect.appendChild(option);
  }

  // New cloth name input
  const nameLabel = document.createElement("label");
  nameLabel.textContent = "New Cloth Name:";
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.style.display = "block";
  nameInput.style.marginBottom = "10px";

  // New cloth type select
  const typeLabel = document.createElement("label");
  typeLabel.textContent = "New Cloth Type:";
  const typeSelect = document.createElement("select");
  typeSelect.style.display = "block";
  typeSelect.style.marginBottom = "10px";
  clothTypes.forEach(type => {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    typeSelect.appendChild(option);
  });

  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Submit";
  submitBtn.style.marginRight = "10px";
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";

  form.appendChild(selectLabel);
  form.appendChild(clothSelect);
  form.appendChild(nameLabel);
  form.appendChild(nameInput);
  form.appendChild(typeLabel);
  form.appendChild(typeSelect);
  form.appendChild(submitBtn);
  form.appendChild(cancelBtn);
  modal.appendChild(form);
  document.body.appendChild(modal);

  submitBtn.addEventListener("click", async () => {
    const clothId = clothSelect.value;
    const newName = nameInput.value.trim();
    const newType = typeSelect.value;

    if (newName === "") {
      alert("Please enter a new cloth name.");
      return;
    }

    // Send request to update cloth
    try {
      const response = await fetch("/api/closet/update", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          cloth_id: clothId,
          name: newName,
          cloth_type: newType
        })
      });

      if (!response.ok) {
        throw new Error("Failed to update cloth.");
      }

      // Update cloth in the UI
      for (let i = 0; i < items.length; i++) {
        if (items[i].getAttribute("data-id") === clothId) {
          items[i].textContent = `${newName} (${newType})`;
          items[i].setAttribute("data-name", newName);
          items[i].setAttribute("data-type", newType);
          break;
        }
      }

      document.body.removeChild(modal);
    } catch (error) {
      console.error("Error updating cloth:", error);
      alert("Error updating cloth.");
    }
  });

  cancelBtn.addEventListener("click", () => {
    document.body.removeChild(modal);
  });
}

async function fetchClothingRecommendation(city) {
  const weatherData = await fetchWeatherData(city);
  const currentWeather = weatherData.weatherConditions;
  const currentTemp = weatherData.temperature;
  try {
    const response = await fetch(`/api/ai/clothes?city=${encodeURIComponent(city)}&weather=${encodeURIComponent(currentWeather)}&temp=${encodeURIComponent(currentTemp)}`);
    if (!response.ok) {
      throw new Error("Failed to fetch clothing recommendation.");
    }
    const data = await response.json();
    
    const recommendationHtml = marked.parse(data.recommendation);
    
    // Display the recommendation on the page (for example, in an element with id="aiRecommendation")
    const recElement = document.getElementById("aiRecommendation");
    if (recElement) {
      recElement.innerHTML = recommendationHtml;
    }
  } catch (error) {
    console.error("Error fetching recommendation:", error);
    alert("Error fetching clothing recommendation.");
  }
}

// Attach event listeners to buttons
document.getElementById("addCloth").addEventListener("click", addCloth);
document.getElementById("removeCloth").addEventListener("click", removeCloth);
document.getElementById("updateCloth").addEventListener("click", updateCloth);

window.addEventListener('DOMContentLoaded', async () => {
  if (USER_ID === null) {
    try {
        const response = await fetch("/api/user");
        if (!response.ok) throw new Error("Failed to fetch user ID");
        const data = await response.json();
        USER_ID = data.user_id;
        // console.log("Fetched user ID inside readCloth:", USER_ID);
    } catch (error) {
        console.error("Error fetching user ID:", error);
        alert("Error fetching user ID. Please try again.");
        return;
    }
  }

  try {
    const response = await fetch("/api/closet");
    if (!response.ok) {
      const errorText = await response.text();  // Get the response text for debugging
      console.error(`Failed to fetch clothes. Status: ${response.status}, Response: ${errorText}`);
      throw new Error("Failed to fetch clothes.");
    }
    const data = await response.json();
    const clothesList = document.getElementById("clothesList");

    // Clear the current list
    clothesList.innerHTML = "";

    // Add each item to the list
    data.forEach(cloth => {  // Use `data` directly, no need for `.clothes`
      const li = document.createElement("li");
      li.textContent = `${cloth.name} (${cloth.cloth_type})`;
      li.setAttribute("data-id", cloth.id);
      clothesList.appendChild(li);
    });
  } catch (error) {
    console.error("Error fetching clothes:", error);
  }

  try {
    // Fetch user's city from backend
    const locationResponse = await fetch("/get_user_location");
    if (!locationResponse.ok) throw new Error("Failed to fetch location");

    const locationData = await locationResponse.json();
    const city = locationData.location;
    fetchClothingRecommendation(city);
  } catch (error) {
    console.error("Error fetching user location:", error);
    const infoDiv = document.querySelector(".info");
    infoDiv.innerHTML = `<p>Error fetching user location: ${error.message}</p>`;
  }
});
