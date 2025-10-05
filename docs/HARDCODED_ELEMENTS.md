# Hardcoded Elements for Client Configuration

This document tracks all client-specific hardcoded elements and their current configuration for West Health demo.

## Current Client: West Health (Demo)
**Last Updated**: 2025-08-12

## 1. Company Information

### Company Name
- **UI Display Name**: "West Health Assistant"
  - Location: `static/index.html` (title, spans)
  - Location: `static/translations.js` (titles)
- **Backend/API Name**: "YourPharmacy Health"
  - Location: `app/core/deterministic.py` (responses)
  - Location: `app/core/agent.py` (system prompt)

### Phone Numbers
- **Primary Customer Service**: 1-844-708-1821
  - Location: `app/core/deterministic.py` (phone response)
  - Location: `app/utils/markdown_formatter.py` (phone patterns)
- **Previous (removed)**: 1-800-922-7538, 1-800-KRO-GERS

### Business Hours
- **Location**: `app/core/deterministic.py` (hours response)
- **Current Values**:
  - Mon, Wed & Fri: 9 AM - 5:30 PM EST
  - Tue & Thu: 10 AM - 6:30 PM EST
  - Customer Service: Mon-Fri 7am-Midnight, Sat-Sun 7am-9:30pm EST

## 2. URLs and Web Properties

### Main Website
- **URL**: https://yourpharmacy.example.com
- **Location**: Multiple files for source formatting

### Store Locator
- **URL**: https://yourpharmacy.example.com/locations
- **Location**: `app/core/deterministic.py` (location response)

### Maps Search Query
- **Query**: "pharmacy+near+me"
- **Location**: `app/core/deterministic.py` (location response)

### Insurance Page
- **URL**: https://yourpharmacy.example.com/insurance-savings
- **Location**: `app/core/deterministic.py` (insurance response)

## 3. Service Descriptions

### Location Count
- **Value**: "numerous locations across multiple states" (generalized)
- **Location**: `app/core/deterministic.py`
- **Previous**: "2,200+ locations across 35 states"

### Service Types
- **Location**: `app/core/deterministic.py` (services response)
- **Values**:
  - Vaccinations (COVID-19, flu shots, routine vaccines)
  - Health screenings & testing
  - Medication services & pharmacy support
  - Food as Medicine programs
  - 340B pharmacy solutions

## 4. RAG Configuration

### Source URL Transformation
- **Pattern**: `www.yourpharmacy.example.com_` → `https://www.yourpharmacy.example.com/`
- **Location**: `app/core/agent.py` (source formatting)
- **Location**: `app/utils/markdown_formatter.py`
- **Previous**: `www.krogerhealth.com_` → `https://www.krogerhealth.com/`

## 5. Formatting Preferences

### Markdown Settings
- **Use Bold Headers**: Yes (`**text**`)
- **Use Bullet Points**: Yes (`•`)
- **Format Phone as Tel Links**: Yes
- **Format URLs as Markdown Links**: Yes
- **Use Emojis**: Yes (though not required)

## 6. Language Support

### Supported Languages
- English (`en`)
- Spanish (`es`)

### Spanish Translations
- All greeting/deterministic responses have Spanish versions
- System prompts have Spanish versions

## Current West Health Configuration

```json
{
  "client_id": "west_health",
  "company": {
    "ui_name": "West Health Assistant",
    "backend_name": "YourPharmacy Health",
    "tagline": "Your health and wellness partner"
  },
  "contact": {
    "phone": {
      "primary": "1-844-708-1821"
    },
    "hours": {
      "customer_service": {
        "weekday": "7 a.m. - Midnight EST",
        "weekend": "7 a.m. - 9:30 p.m. EST"
      },
      "pharmacy": {
        "mon_wed_fri": "9 AM - 5:30 PM EST",
        "tue_thu": "10 AM - 6:30 PM EST"
      }
    }
  },
  "urls": {
    "main_site": "https://yourpharmacy.example.com",
    "store_locator": "https://yourpharmacy.example.com/locations",
    "insurance": "https://yourpharmacy.example.com/insurance-savings",
    "maps_query": "pharmacy+near+me"
  },
  "locations": {
    "count": "numerous",
    "states": "multiple",
    "description": "numerous locations across multiple states"
  },
  "services": [
    "Vaccinations",
    "Health screenings",
    "Medication services",
    "Food as Medicine",
    "340B pharmacy solutions"
  ],
  "formatting": {
    "use_markdown": true,
    "format_phone_links": true,
    "format_url_links": true,
    "use_bold_headers": true,
    "use_bullet_points": true
  },
  "languages": ["en", "es"]
}
```

## Client Migration Checklist

### Files to Update (in order):

#### 1. Frontend UI Files
- [ ] `static/index.html`
  - Title tag
  - Assistant title span (id="assistantTitle")
  - Description paragraph (id="assistantDescription")
  - Welcome message in chat bubble (id="welcomeContent")
- [ ] `static/translations.js`
  - title (English & Spanish)
  - description (English & Spanish)
  - welcomeTitle (English & Spanish)

#### 2. Backend Response Files
- [ ] `app/core/deterministic.py`
  - greeting responses (lines 24-25)
  - location responses (lines 43-53)
  - phone responses (lines 57-71)
  - insurance URL (line 83)
  - services responses (lines 96, 128, 130, 162)
  - Pattern matching for locations (lines 252-254, 294)
- [ ] `app/core/agent.py`
  - System prompts (already uses YourPharmacy)
  - Source URL formatting (lines 479-528)
- [ ] `app/utils/markdown_formatter.py`
  - Phone patterns (lines 15-17)
  - URL patterns (lines 23-28)
  - Source URL transformations (lines 93-102)

#### 3. Documentation
- [ ] `docs/HARDCODED_ELEMENTS.md` - Update this file with new client config

### Quick Replace Guide

| Search For | Replace With (Example) |
|------------|----------------------|
| West Health Assistant | [New Client] Assistant |
| YourPharmacy Health | [New Client] Health |
| 1-844-708-1821 | [New Phone Number] |
| yourpharmacy.example.com | [New Domain] |
| pharmacy+near+me | [client]+pharmacy+near+me |

### Testing Checklist
- [ ] Clear browser cache (Ctrl+F5)
- [ ] Verify UI shows correct branding
- [ ] Test greeting response
- [ ] Test phone number response
- [ ] Test location response
- [ ] Test Spanish language toggle
- [ ] Verify RAG responses use correct company name

## Migration Notes

1. Create a `ClientConfig` class to load and validate configuration
2. Replace all hardcoded values with config lookups
3. Add environment variable for `CLIENT_ID` to select configuration
4. Create configuration files for each client
5. Add configuration validation on startup
6. Support dynamic response templates based on client config