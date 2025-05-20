document.addEventListener("DOMContentLoaded", () => {
  startWeatherTracking();
  function startWeatherTracking() {
    if (!navigator.geolocation) {
      return;
    }

    navigator.geolocation.watchPosition(
        async (position) => {
          const {latitude, longitude} = position.coords;

          try {
            // Lấy dữ liệu thời tiết
            const weatherResponse = await fetch(
                `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,weathercode`
            );
            const weatherData = await weatherResponse.json();

            const temperature = weatherData.current.temperature_2m;
            const weatherCode = weatherData.current.weathercode;

            // Lấy tên vị trí qua Nominatim
            const locationResponse = await fetch(
                `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`
            );
            const locationData = await locationResponse.json();

            const locationName =
                locationData.address.city ||
                locationData.address.town ||
                locationData.address.village ||
                "Không xác định";

            // Hiển thị thông tin thời tiết + vị trí với icon
            document.querySelector(".weather-widget").innerHTML = `
          <div class="text-center">
            <p class="text-base font-semibold text-gray-600">${locationName}</p>
            <p class="text-sm">${temperature}°C, ${getWeatherDescriptionWithIcon(weatherCode)}</p>
            <p class="text-xs text-gray-500">Cập nhật: ${new Date().toLocaleString()}</p>
          </div>
        `;
          } catch (error) {
          }
        },
        (error) => {
        },
        {
          enableHighAccuracy: true,
          maximumAge: 10000,
          timeout: 10000,
        }
    );
  }

  function getWeatherDescriptionWithIcon(code) {
    if ([0].includes(code)) return "☀️ Trời quang";
    if ([1, 2, 3].includes(code)) return "⛅ Nhiều mây";
    if ([45, 48].includes(code)) return "🌫️ Sương mù";
    if ([51, 53, 55].includes(code)) return "🌦️ Mưa phùn";
    if ([61, 63, 65].includes(code)) return "🌧️ Mưa";
    if ([71, 73, 75].includes(code)) return "❄️ Tuyết rơi";
    if ([80, 81, 82].includes(code)) return "🌧️ Mưa rào";
    if ([95, 96, 99].includes(code)) return "⛈️ Giông bão";
    return "❓ Không xác định";
  }
});