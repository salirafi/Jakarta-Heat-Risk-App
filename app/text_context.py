LANG = {
    "id": {
        "page_title": "Peta dan Prakiraan Risiko Panas Jakarta",
        "page_subtitle": "Informasi indeks dan risiko panas di seluruh wilayah Jakarta berdasarkan data BMKG.",

        "heat_risk_map": "Peta risiko panas",
        "avg_conditions": "Nilai rerata parameter setiap kota di Jakarta",
        "avg_note": "Nilai rerata untuk temperatur, kelembapan, dan indeks panas yang dihitung dari seluruh kelurahan di kota terkait.",

        "current_conditions": "Kondisi saat ini dan prakiraan mendatang",
        "future_forecast": "Prakiraan mendatang pada lokasi yang dipilih",
        "heat_index_over_time": "Evolusi indeks panas pada lokasi yang dipilih",

        "city_regency": "Kota / Kabupaten",
        "kecamatan": "Kecamatan",
        "kelurahan": "Kelurahan / Desa",

        "temperature": "Temperatur",
        "humidity": "Kelembapan",
        "heat_index": "Indeks Panas",
        "risk": "Risiko",
        "weather": "Cuaca",

        "heat_risk_guide": "Panduan risiko panas",
        "guide_intro": "Klik salah satu tingkat risiko panas untuk melihat definisi dan tindakan yang disarankan untuk tingkat terkait. Panduan ini berdasarkan ",

        "footer_credit": "© Sayyed Ali Rafi",

        "reference_title": "Catatan dan Referensi",
        "reference_content": """
        1. Indeks panas dihitung menggunakan formulasi regresi dari US National Weather Service ([lihat di sini](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) dan [di sini](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), dengan konversi suhu dari Celsius ke Fahrenheit dan sebaliknya. Formulasi ini pada dasarnya ditujukan untuk wilayah di sekitar Amerika Serikat, sehingga mungkin tidak sepenuhnya akurat untuk kondisi tropis di Jakarta, tetapi tetap memberikan perkiraan risiko panas yang berguna.
        
        2. Tabel batas wilayah administratif diambil dari basis data RBI10K_ADMINISTRASI_DESA_20230928 oleh Badan Informasi Geospasial (BIG).

        3. Kode wilayah administratif diambil dari [wilayah.id](https://wilayah.id/) berdasarkan Kepmendagri No 300.2.2-2138 Tahun 2025.

        4. Tabel prakiraan cuaca diambil dari Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) yang dapat diakses melalui [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).
        
        5. Penggunaan *generative AI* meliputi: Visual Studio Code Copilot untuk membantu merapikan kode dan menulis komentar dan *docstring*, serta OpenAI ChatGPT untuk mencari ide untuk `syntax` kode dan identifikasi *runtime error*. Selebihnya, termasuk perumusan masalah dan *brainstorming* kerangka berpikir, perunutan logika dan penulisan kode utama dari *database management* di SQLite hingga pengembangan *web app* dengan Shiny dikerjakan oleh *author* sepenuhnya.
        """,
    },

    "en": {
        "page_title": "Jakarta's Heat Risk Map and Forecast",
        "page_subtitle": "Heat index and risk information throughout Jakarta region based on BMKG data. ",

        "heat_risk_map": "Heat risk map",
        "avg_conditions": "Average conditions across Jakarta cities",
        "avg_note": "Averaged across all wards within each city at the selected map time.",

        "current_conditions": "Current conditions and near-term forecast",
        "future_forecast": "Future forecasts at selected location",
        "heat_index_over_time": "Heat index over time at selected location",

        "city_regency": "City / Regency",
        "kecamatan": "Subdistrict",
        "kelurahan": "Ward",

        "temperature": "Temperature",
        "humidity": "Humidity",
        "heat_index": "Heat Index",
        "risk": "Risk",
        "weather": "Weather",

        "heat_risk_guide": "Heat risk guide",
        "guide_intro": "Click a heat risk level below to see what it means and what actions to take. This guide is based on the ",

        "footer_credit": "© Sayyed Ali Rafi (salirafi8@gmail.com)",

        "reference_title": "Notes and References",
        "reference_content": """
        1. Heat index is computed using the regression formula from the US National Weather Service ([see here](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) and [here](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), with Celcius to Fahrenheit conversion and vice versa. The formulation is expected to be valid for US sub-tropical region, but its use for tropical region like Indonesia does not guarantee very accurate results. However, as first-order approximation, this is already sufficient.

        2. Administrative regional border data is retrieved from RBI10K_ADMINISTRASI_DESA_20230928 database provided by Badan Informasi Geospasial (BIG).

        3. Administrative regional code is taken from [wilayah.id](https://wilayah.id/) based on Kepmendagri No 300.2.2-2138 Tahun 2025.

        4. Weather forecast data is taken from the public API of Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) accessed via [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).

        5. The use of generative AI includes: Visual Studio Code's Copilot to help tidying up code and writing comments and docstring, as well as OpenAI's Chat GPT to give code syntax ideas and identify runtime error. Outside of those, including problem formulation and framework of thinking, code logical reasoning and writing, from database management using SQLite to web development using Shiny, all is done solely by the author. 
        """,
    }
}

HEAT_RISK_GUIDE = {
    "id": {
        "Lower Risk": {
            "level": "Level 0 · Sedikit hingga Tidak Ada",
            "expect": (
                "Tingkat panas ini menimbulkan sedikit hingga tidak ada peningkatan risiko "
                "bagi kebanyakan orang. Tingkat panas ini sangat umum dan "
                "biasanya tidak memerlukan tindakan pencegahan khusus."
            ),
            "do": (
                "Cukup menjaga hidrasi dasar dan tetap sadar terhadap kondisi panas."
            ),
        },
        "Caution": {
            "level": "Level 1 · Ringan",
            "expect": (
                "Sebagian besar orang masih dapat mentoleransi panas ini, tetapi ada risiko "
                "ringan terhadap dampak dari panas bagi orang yang sangat sensitif terhadap panas,"
                "khususnya saat berada di luar "
                "ruangan tanpa pendinginan yang memadai atau tanpa hidrasi yang cukup."
            ),
            "do": (
                "Perbanyak minum, kurangi waktu di luar ruangan di saat matahari yang paling terik, "
                "berteduh, dan manfaatkan udara malam yang lebih sejuk bila memungkinkan."
            ),
        },
        "Extreme Caution": {
            "level": "Level 2 · Sedang",
            "expect": (
                "Banyak orang masih dapat mentoleransi panas ini, tetapi risikonya menjadi lebih "
                "tinggi bagi kelompok rentan akan panas, terutama mereka yang tanpa pendinginan dan hidrasi memadai, pendatang atau orang luar yang belum terbiasa dengan "
                "kondisi panas, dan orang yang menghabiskan waktu lama di luar ruangan. "
                "Gangguan kesehatan akibat panas mulai dapat terjadi."
            ),
            "do": (
                "Kurangi waktu di bawah sinar matahari di saat-saat yang paling terik, "
                "tetap terhidrasi, tetap berada di tempat yang sejuk, dan tunda atau pindahkan aktivitas luar "
                "ruangan ke jam-jam yang lebih sejuk."
            ),
        },
        "Danger": {
            "level": "Level 3 · Tinggi",
            "expect": (
                "Ini adalah tingkat risiko panas yang tinggi. Kondisi berbahaya dapat memengaruhi "
                "bagian populasi yang jauh lebih besar, terutama siapa pun yang aktif di bawah "
                "matahari atau tanpa pendinginan dan hidrasi yang memadai."
            ),
            "do": (
                "Pertimbangkan untuk membatalkan aktivitas luar ruangan pada waktu terpanas, "
                "tetap terhidrasi, tetap berada di dalam ruangan yang lebih sejuk, dan gunakan AC "
                "jika tersedia. Kipas angin saja mungkin tidak cukup."
            ),
        },
        "Extreme Danger": {
            "level": "Level 4 · Ekstrem",
            "expect": (
                "Ini adalah tingkat risiko panas yang langka dan sangat ekstrem. Kondisi ini "
                "sering mencerminkan kejadian panas berkepanjangan selama beberapa hari dan dapat "
                "berbahaya bagi seluruh populasi, terutama mereka yang tanpa pendinginan memadai."
                "Pada tingkat ini, kondisi dapat mematikan."
            ),
            "do": (
                "Benar-benar pertimbangkan untuk membatalkan aktivitas luar ruangan, tetap terhidrasi, "
                "tetap berada di tempat yang sejuk termasuk pada malam hari, gunakan AC jika "
                "tersedia, dan periksa tetangga, kerabat, atau orang lain yang rentan."
            ),
        },
    },

    "en": {
        "Lower Risk": {
            "level": "Level 0 · Little to None",
            "expect": (
                "This level of heat poses little to no elevated risk for most people. "
                "It is a very common level of heat and usually does not require special precautions."
            ),
            "do": (
                "No special preventive action is usually needed. "
                "Basic hydration and normal heat awareness are enough."
            ),
        },
        "Caution": {
            "level": "Level 1 · Minor",
            "expect": (
                "Most people can tolerate this heat, but there is a minor risk of heat-related effects "
                "for people who are extremely heat-sensitive and those without effective cooling or enough hydration."
            ),
            "do": (
                "Increase hydration, reduce time outdoors during the strongest sun, stay in the shade, "
                "and use cooler nighttime air when possible."
            ),
        },
        "Extreme Caution": {
            "level": "Level 2 · Moderate",
            "expect": (
                "Many people can still tolerate this heat, but the risk becomes more noticeable for "
                "heat-sensitive groups especially those without effective cooling or hydration, visitors not acclimated to the heat, and people spending long "
                "periods outside. Heat-related illness can begin to occur."
            ),
            "do": (
                "Reduce time in the sun during the warmest part of the day, stay hydrated, stay in a cool "
                "place, and move outdoor activities to cooler hours."
            ),
        },
        "Danger": {
            "level": "Level 3 · Major",
            "expect": (
                "This is a major heat risk. Dangerous conditions can affect a much larger part of the "
                "population, especially anyone active in the sun or without proper cooling and hydration."
            ),
            "do": (
                "Consider canceling outdoor activity during the hottest part of the day, stay hydrated, "
                "remain in cooler indoor places, and use air conditioning if available. Fans alone may not be enough."
            ),
        },
        "Extreme Danger": {
            "level": "Level 4 · Extreme",
            "expect": (
                "This is a rare and extreme level of heat risk. It often reflects a prolonged multi-day "
                "heat event and can be dangerous for the entire population, especially without cooling."
            ),
            "do": (
                "Strongly consider canceling outdoor activities, stay hydrated, stay in a cool place "
                "including overnight, use air conditioning if available, and check on neighbors or other vulnerable people."
            ),
        },
    },
}
