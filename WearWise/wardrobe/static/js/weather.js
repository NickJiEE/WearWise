document.addEventListener('DOMContentLoaded', function() {
    const weatherForm = document.getElementById('weatherForm');
    if (weatherForm) {
        weatherForm.addEventListener('submit', function(event) {
            event.preventDefault();
            console.log('Form submitted successfully');
            const city = document.getElementById('city').value;
            displayWeather(city);
        });
    } else {
        console.log('Weather form not found on this page.');
    }
});

async function fetchWeatherData(city) {
    const nominatimUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(city)}&format=json`;

    try {
        const nominatimResponse = await fetch(nominatimUrl);

        if (!nominatimResponse.ok) throw new Error('Failed to fetch data from Nominatim API');

        const nominatimData = await nominatimResponse.json();
        // console.log('Nominatim Data:', nominatimData);

        if (!nominatimData || nominatimData.length === 0) throw new Error('City not found');

        const lat = nominatimData[0].lat;
        const lon = nominatimData[0].lon;

        const weatherPointsUrl =`https://api.weather.gov/points/${lat},${lon}`;
        const pointsResponse = await fetch(weatherPointsUrl, {
            headers: {
                'User-Agent': 'YourAppName/1.0 (your@email.com)'
            }
        });
        // console.log('Points Response:', pointsResponse);

        if (!pointsResponse.ok) throw new Error('Failed to fetch weather points data');

        const pointsData = await pointsResponse.json();
        // console.log('Points Data:', pointsData);

        if (!pointsData.properties || !pointsData.properties.forecast) throw new Error('Forecast URL not found');

        const forecastUrl = pointsData.properties.forecast;

        const forecastResponse = await fetch(forecastUrl, {
            headers: {
                'User-Agent': 'YourAppName/1.0 (your@email.com)'
            }
        });
        // console.log('Forecast Response:', forecastResponse);

        if (!forecastResponse.ok) throw new Error('Failed to fetch forecast data');

        const forecastData = await forecastResponse.json();
        // console.log('Forecast Data:', JSON.stringify(forecastData, null, 2));

        if (!forecastData.properties || !forecastData.properties.periods || forecastData.properties.periods.length === 0) {
            throw new Error('Invalid forecast data structure: Missing periods');
        }

        return {
            location: nominatimData[0].display_name,
            weatherConditions: forecastData.properties.periods[0].shortForecast || 'No forecast available',
            temperature: forecastData.properties.periods[0].temperature || 'N/A',
            weatherIconUrl: forecastData.properties.periods[0].icon
        };

    } catch (error) {
        console.error('Error fetching weather data:', error);
        const infoDiv = document.querySelector('.info');
        infoDiv.innerHTML = `<p>Error: ${error.message}</p>`;
        return {
            location: 'Unknown',
            weatherConditions: 'Unknown',
            temperature: 'N/A',
            weatherIconUrl: ''
        };
    }
}

async function displayWeather(city) {
    const weatherData = await fetchWeatherData(city);
    
    let cityImage = '';
        if (city.toLowerCase() === 'new york city, ny' || city.toLowerCase() === 'new york city' || city.toLowerCase() === 'nyc') {
            cityImage = '/static/New York City.jpg';
        } else if (city.toLowerCase() === 'san diego, ca' || city.toLowerCase() === 'san diego') {
            cityImage = '/static/San Diego.jpg';
        } else if (city.toLowerCase() === 'brooklyn, oh') {
            cityImage = '/static/Brooklyn OH.jpg';
        } else if (city.toLowerCase() === 'los angeles, ca' || city.toLowerCase() === 'los angeles' || city.toLowerCase() === 'la') {
            cityImage = '/static/Los Angeles.jpg';
        }

    const infoDiv = document.querySelector('.info');
    infoDiv.innerHTML = `
        <p><strong>Location:</strong> ${weatherData.location}</p>
        <p><strong>Weather Conditions:</strong> ${weatherData.weatherConditions}</p>
        <p><strong>Temperature:</strong> ${weatherData.temperature}°F</p>
        ${cityImage ? `<img src="${cityImage}" alt="City Image" style="width: 700px; height: auto;">` : ''}
        ${weatherData.weatherIconUrl ? `<img src="${weatherData.weatherIconUrl}" alt="Weather Condition Image" style="width: 700px; height: auto;">` : ''}
    `;
}
