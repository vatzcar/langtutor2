LANGTUTOR

## 1. DESCRIPTION
LangTutor is a freemium service that allows users to learn a language with the help of AI virtual tutor in a digital classroom. Users can have video call with the AI tutor to learn their desired language and progress from CEFR level A0 through C2.

## 2. Core Architecture
- Backend: FastAPI (Python)
- Frontend: Flutter (Mobile-first)
- AI Live Video Generation: LiveKit (WebRTC Transport) + LivePortrait + livekit-plugins-avatartalk + Fish Speech S2 + Deepgram (Self-Hosted)
- Logic/Brain: Gemini 1.5 Flash 

## 3. AI Live Video Generation (CRITICAL)
- We MUST use `LivePortrait` (TensorRT optimized) via the `livekit-plugins-avatartalk` plugin.
- We MUST use `Fish Speech S2` for local TTS.
- We must usee `Deepgram` for local STT.
- API-based video services like LemonSlice or HeyGen are strictly forbidden due to cost.

## 4. Application Logic

## 4.1. Admin

## 4.1.1. User Management
- User ACL. Configurable user roles, end-user, configured admin roles.
- All the features of API/actions should be configurable for admin roles
- Manage end-user. Add, Edit, enable/disable, delete (soft-delete)
- Edit user profile data
- Managing user subscription. Assign a subscription and/or update subscription expiry
- Manage admin. Add, edit, enable/disable, delete (soft-delete)
- User ban list. Add user to ban list with ban expiry. Unban a user

## 4.1.2. Language
- All languages configurable. Add, edit, enable/disable, delete (soft-delete)
- Languages should have icon to upload
- Short code of language should be the locale (like en-GB, en-US, it-IT)
- There could be several languages with same name but locale must the unique
- Languages will have a default column(flag). This flag is to detect the default locale for a language (like 'es-ES' should be default for all the Spanish locale)
- Languages will have a fallback column (flag). But only one language can have fallback flag enabled. If fallback is enabled for one language, the flag will set to false for all other languages.

## 4.1.3. Personas
- Configurable personas (AI avatars). Add, edit, enable/disable, delete (soft-delete)
- Personas will be linked with a language
- Personas will have a name
- Personas will have image (portrait)
- Personas will have gender
- Personas will have type - Teacher, Coordinator, Peer
- One language can only have one Coordinator persona

## 4.1.4. Plan management
- Pre-existing plans in database
- Free plan - charges $0 (or equivalant local currency)
- Free plan will have configurable voice call limit (in minute) per day
- Free plan will have configurable text-based learning limit (in minute) per day
- Free plan is editable only on voice call, and text-based learning limits
- Paid plan - Pro, Ultra
- Both the paid plan is editable; its price and limits only
- Both the plan has monthly and yearly billing cycle
- The price for monthly and yearly billing cycle for both the plan are editable
- Both the paid plan will have configurable text-based learning limits (in minute) per day. Value 0 for text-based learning will be considered unlimited
- Both the paid plan will have configurable voice call limits (in minute) per day. Value 0 for voice call will be considered unlimited
- Both the paid plan will have configurable video call limits (in minute) per day. Value 0 for video call will be considered unlimited
- Both the paid plan will have configurable agentic support voice call limit per month. Value 0 for voice call will be considered unlimited
- Both the paid plan will have configurable coordinator support video call limit per month. Value 0 for video call will be considered unlimited
- All the plans (including free plan) will have unlimited text based learning
- There will be no rollover of any unused time (for time restricted features) for any plan
- Users are allowed to change plan (upgrade/downgrade) or billing cycle. And balance will be calculated on pro-rata basis
- Apple/Google in-app purchase payment method to be used as payment processor

## 4.1.5. Reports/Logs
- All events/action will have detailed log (like actor, action, timestamp etc)
- The log page will allow to sort and filter the log on all the columns also allowing filter/sort on multiple columns
- Searchable session transcript. Filtered by user, language, date (each or multiple)
- User report for user registration and activity
- New user registration report (during the period): Daily, Weekly, Monthly, Yearly, From Start, Custom date range
- Active users report (Logged in during the period): Daily, Weekly, Monthly, Yearly, From Start, Custom date range
- User Engagement report: Average Engagement Time -  Overall, Language-wise, CEFR Level-wise
- Language Analytics (Most-Least): Users, Geo Location (country), Personas

## 4.2. Mobile App

## 4.2.1. Sign-up/Sign-in
- Only using mobile platform's social login

## 4.2.2. Onboarding
- After sign-up user will go through onboarding process
- For onboarding, user will be taken into a video call where the persona (AI coordinator) will determine the users native language and CEFR level
- Once the onboarding is complete, user will be taken to a screen where three plans will be shown; Free, Pro, Ultra to make user choose the desired plan
- On plan selection plan, by default annual cycle must be selected. On top of plan cards, there should be a slider switch to switch between monthly and annual cycle
- On monthly and annual switch, under annual it should show how much user is saving with annual cycle. Also each plan card should show the benefits offered for the plan

## 4.2.2.1. Onboarding flow
- Right after sign-up user will be taken to a video call with a coordinator
- The language of coordinator will be auto-detected. For auto-detection phone language should be detected and then with IP goelocation should be detected to build the locale. If a user is having English set in phone as language and the geolocation of IP is from UK, it'll assume the locale to be 'en-UK'. Similarly a user with Spanish as phone language and geolocation of IP in Mexico should be detected as 'es-MX'
- If the language is detected but geoip isn't matching with any locale (like phone language is Spanish but geoip is China) then system should select the default (column/flag) locale of the language
- After auto-detection of the locale, the persona (coordinator) should be shown for the same locale
- The persona (coordinator) should ask user to confirm the auto-detected language. If user mention different the locale should change
- When persona (coordinator) asks user to confirm the language, if user doesn't confirm, system should select the fallback language
- The persona should remian same for the entire call even if the language changed
- If user's language is not available in the system, the language should fallback to the language configured as fallback language. The persona (coordinator) should inform user that their language is not yet available so the system has fallen back to the [FALLBACK_LANGUAGE]
- Then the persona should ask the user which language they want to learn also with the country (if same language is available in different countries) to detect the locale
- Next the persona should continue the talk with the user to deternine their CEFR level of the language the user wants to learn. The test should be through a mix of conversation and textual quiz
- Once the CEFR level is identified properly, the user should be given choice to select their teacher from available list of the teachers for the language
- Besides choosing the teacher user will have the option to select teaching style (Casual and Friendly, Friendly but Structured, Formal and Structures)
- After teacher selection the call should end and user should be taken to a page where user will enter their name, date of birth (optional but encouraged), and choose avatar from the list
- In next page user will select a plan for their account
- And after selecting the plan user will be taken to home screen

## 4.2.3. Learning
- The user will learn from detected CEFR level to C1 level
- The prosona (teacher) will use native language of the student to teach the language till user reaches CEFR level B2
- While teaching, there will be almost no topic overlap from upper CEFR level, but will always use topics from all lower CEFR levels to reinforce the past knowledge
- During the call (audio and video both) transcript of the personas' conversation will be shown as subtitle text
- During a lession user may be taken to a text based screen to test the user (textbox/textarea for writing or flat button(s) for selecting an option or flat buttons to cross-match items from two columns)
- When presenting the text-based screen, system should terminate the media stream to reduce the load on AI server
- AI should structure the lessions dynamically based on user's weakness and interests and make the learning fun and interesting for the user
- When all the topic for a CEFR level is covered, AI should test the user to see if they really can pass the level
- If user fails to pass the test, persona (teacher) should continue teaching the same level strategizing the lessions focusing on the weakness of the user while touching other topics time to time. After a short while the persona (teacher) should inform the user that user may ask for re-taking the test (at the end of each lession)
- Both the video call and voice call will use phone speaker (hands-free) for audio
- User may text chat with persona (teacher) to learn instead of having a call

## 4.2.4. Practice
- User may practice what they have learnt so far to increase their skill
- User may go to 'Practice Hub' to practice the language
- Under practice mode, the persona (teacher) will not teach anything new but only help and teach what the user has learnt so far

## 4.2.5. User Profile
- Personal Data tab: shows user's name, avatar, date of birth, country
- User may edit their name, date of birth, and native language
- CEFR level tab: shows the journey of the user on each day (day of learning, like , "Day 1", "Day 2"...) with percent of topic learned for the current CEFR level of the selected language
- History tab: shows the day of learning (like , "Day 1", "Day 2"...), Date, link to transcript of the call for the selected language
- Subscription tab: shows current subscription of the user and possibility of change the plan
- Clicking on change plan button user may change the plan (upgrade/downgrade) or change the billing cycle of current plan

## 4.2.6. Support
- Support page will show user two options; "Call", "Chat", "History"
- Call will let user make a voice/video call to AI agent to receive the support on the issue faced by the user
- Call support will be limited by the plan's limitation
- All support calls will have transcripts
- Chat will let user chat with AI agent to get support on the issue the user is facing
- History will show list of past calls/chats, with AI generated 'Title' and 'Date'
- Tapping on a item on list of historical support will open a page with past chat/call transcript

## 4.2.7. App Design
- The app design should be modern, professional, minimalist with pastel colors
- The app should have a color scheme which represent casual (fun) mood but also eye pleasing and should be appropriate for the users of all the ages
- Each screen should have different colored BG image (flat color with subtle transparent bubbles)
- Screen mockups are stored in "Screens" folder in current folder
- All the different shades of gray used in mockup to to separate blocks frron one to another. The color selection should be to made to look the interface professional
- All the disabled elements across the app will be monochrome gray besides being unresponsive

## 4.2.7.1. Home Screen
- Reference mockup 'home.png'
- Top bar has four information
- First (from left) is Language flag of selected language (`LANG FLAG` block in the mockup)
- Next block shows the current CEFR level of the user for the selected language (block `CEFR LEVEL`)
- Next block shows the progress of current CEFR level in percent (block `PROGRESS PCT (%)`)
- Next block shows the current subscription plan of the user (block `PLAN_NAME`)
- Clocking on language flag (block `LANG FLAG`) will open the language popup (reference mockup 'home-lang-popup.png')
- In popup, top row shows all the languages user is learning right now. Languages are represented by flags
- User may click any of the flag to select that language to learn
- Bottom block will show a sperator and a title underneath "Learn A New Language"
- In following block all the languages will show except those user has already started learning (i.e. languages in top row)
- Clicking in any language from this (bottom) block will select that language as the new language and also will initiate the onboarding process for the language
- Onboarding for a language will follow the same process what user has gone through initial onboarding process, except, the system will use user's native language that already in database and will not re-validate it, and after teacher selection, user will be taken to the home screen with the language selected
- clicking/taping anywhere other than a button (flag) will close the popup
- Middle block will show user's profile image in a circular cut
- Underneath that will be block for learning the language
- Left button will have call icon (block with 'call icon' in mockup) that will initiate the voice call
- Next to it (right) will be video call icon (block with 'video call icon' in mockup) that will initiate the video call
- Underneath there will be "CHAT" button (block `CHAT`) that will initiate a text-based chat for learning
- The voice and video icon will be disabled for tapping if the current subscription plan doesn't allow user to use the feature, or if the user has exhauseted the time limit for the feature
- At the footer there will be action bar
- Action bar will be persistant for all the screens
- First icon in action bar shows home icon (block `HOME ICON`). Clicking/taping this icon will take user to home screen of the app
- Next icon is practice icon (block `PRACTICE ICON`). Clicking/taping this icon will take user to practice hub screen
- Next icon is profile icon (block `PROFILE ICON`). Clicking/taping this icon will take user to profile screen
- Next icon is support icon (block `SUPPORT ICON`). Clicking/taping this icon will take user to support screen
- All the icons in action bar will show appropriate icon instead of any text

## 4.2.7.2. Learning - Voice
- Reference mockup 'learning-voice.png'
- Top block shows the image of the persona (teacher) in a circular cut (block `AI Persona (TEACHER) IMAGE`)
- Underneath is the transcript (subtitle) block (block `TRANSCRIPT/SUBTITLE`). This block will show the live transcript of the voice call
- Below this will be control block to control the call
- Left button will be video call button (block with 'video call icon') to switch the call to video call
- Video call button will be disabled if the current subscription plan doesn't allow user to use the feature, or if the user has exhauseted the time limit for the video call
- In middle there will be big round RED stop button (block with circle and square). Tapping this button will end the call and user will redirect to home screen of the app
- On right shows the voice call button (block with 'call icon'). For voice call screen this button should be disabled (to represent that user is currently on voice call)
- If user is about to exceed the time limit for the voice call, 2 minutes before the end of the daily limit, the AI will tell user that in 2 minute the call will end
- On completing the daily time limit, the call will hang up automatically and user will be takem to home screen of the app

## 4.2.7.3. Learning - Video
- Reference mockup 'learning-video.png'
- Top block shows the live video feed of persona (teacher) (block `AI Persona (TEACHER) VIDEO`)
- Underneath is the transcript (subtitle) block (block `TRANSCRIPT/SUBTITLE`). This block shows the live transcript of the video call
- Below this will be control block to control the call
- Left button will be video call button (block with 'video call icon'). For this screen this button should be disabled (to represent that user is currently on video call)
- In middle there will be big round RED stop button (block with circle and square). Tapping this button will end the call and user will be taken to home screen of the app
- On right shows the voice call button (block with 'call icon'). Tapping this button will switch the call to voice call
- Voice call button will be disabled if the current subscription plan doesn't allow user to use the feature, or if the user has exhauseted the time limit for the voice call
- If user is about to exceed the time limit for the video call, 2 minutes before the end of the daily limit, the AI will tell user that in 2 minute the call will end
- On completing the daily time limit, the call will hang up automatically and user will be takem to home screen of the app

## 4.2.7.4. Learning - Chat
- Reference mockup 'learning-chat.png'
- Top bar will have three blocks
- First (from left) block (block `PERSONA IMAGE`) will show the image of the persona (teacher) in a circular cut
- In middle there will be the language flag (block `LANG FLAG`) and next to it is the name of the language (block `LANGUAGE_NAME`)
- On Right corner back button will be shown (block with 'back arrow'). Tapping on this icon will take user to the home screen of the app
- Below shows the messages block. This block will cover majority of the screen. Chat messages will show in baloon in this block. Messages from AI will show on left and messages from user will show on right
- Messages block is a scrollable block. Once the total height of the messages exceed the height of the block, user may scroll to see hidden messages
- If current scroll is to the last message (bottom), the entire block content will automatically scroll up to keep the new messages visible as bottom aligned
- If user scrolls down to see old messages, the message stack will not scroll automatically. A green circle will appear on the bottom right corner of this block on receiving new message, tapping which will scroll to bottom to show all new messages. And new message baloons will have one yellow exclamation icon to notify user a new unread message
- Upon revealing unread message, after 5 seconds the unread messages will be marked as read and the yellow exclamation icons will disappear
- Under the messages block, shows the message input as textbox where user can type the message with a placeholder text (block `Type Your Message`)
- If the typed message is more than one line, the input will change from textbox to textarea with three lines and messages block will shrink to accomodate the extended height of the input field
- Once messaqge posted, the input will trun back to a textbox and messages block will expand to its original height
- Right next to input (inline) will show a send message icon (block with 'paper plane'). Tapping this button will post the message
- If user is about to exceed the time limit for the chat, 2 minutes before the end of the daily limit, the AI post a message that in 2 minute the chat will end
- On completing the daily time limit, the chat will end, inputbox and send message icon will be disabled to prevent user from posting any message, however user may stay at the screen to go through the cat session

## 4.2.7.5. Practice Hub
- Reference mockup 'practice.png'
- Top bar look and functions will be same as home screen
- Under top bar will show the title "PRACTICE HUB" (block `PRACTICE HUB`)
- Below that shows the image of the persona (teacher) in a cicular cut
- Uder that there shows the clock same as learning block of home screen
- The function of the buttons will be same as home screen (launching the voice/video call or chat), except the calls or chat will take user in practice mode and the learning session will follow the practice rules
- In the practice sessions user will not learn anything new but the persona (teacher) will take the user through the topic they have already learnt
- Time for practice sessions will be counted from the daily limit of the subscription plan of the user and time limit behaviour will be same as learning

## 4.2.7.6. Profile - Profile
- Reference mockup 'profile-profile.png'
- The landing screen of profile (tapping the profile icon in action bar)
- Top left shows the current plan user is in
- Top right shows the user menu (reference point 4.2.5)
- First menu item in user menu has Profile page (this page)
- Second menu item shows CEFR icon linked to Profile - CEFR screen
- Third menu item shows History icon linked to Profile - History screen
- Forth menu item shows Subscription icon linked to Profile - Subscription screen
- In the middle shows large profile image of user in round cut
- Below that it shows the user profile data (user information)
- Underneath is "Edit" button that takes user to screen to edit their profile information
- Profile edit screen shows form to edit user information where user may change their `Name`, `Date of Birth`, `Native Language`

## 4.2.7.7. Profile - CEFR
- Reference mockup 'profile-cefr.png'
- The screen which shows detailed CEFR information of user for the currently selcted language
- Top block is having user plan and user menu same across profile screens
- Under that shows the title "CEFR LEVEL"
- Below shows the flag of currently selected language
- Beside that shows the currently selected language (inline to the flag)
- Below that shows all the CEFR level that user has attended in a list
- The list is shown in ascending order (like C1, C2, B1 etc.) and passed levels on top
- Each block in the list shows the CEFR level name (like C1, C2 etc.) and staus (right aligned)
- The CEFR level status shows "Passed" or "IN PROGRESS..."
- Underneath shows the CEFR level analytics
- In analytics it shows the number of lession user has taken, number of hours spent, streaks of learning days, the percentage of the CEFR level covered, number of practice session taken, and total hours of practice session
- By default the analytic block will show the analytics of current CEFR level the user is in
- Tapping on an item in CEFR level list will show the analytics for that level

## 4.2.7.8. Profile - History
- Reference mockup 'profile-history.png'
- Top bar remains same for all the profile screens
- Below show the tyitle "HISTORY"
- Underneath shows the list of days user has taken the session for the selected language
- The list show show as day number (Day 1, Day 2, Day 3 etc.), the date user has taken the session
- And the the link to view the session transcript with the label "View Session"
- The list may repeat a row for same day (and date) for different session (like video, voice, text chat, practice etc.)
- Tapping on "View Session" will take user to trascript page that looks like text chat page (reference mockup learning-chat.png) where the transcript of persona (teacher) will show like the message of the persons (teacher) and transcript of user will show as message of the user
- The block becomes scrollable once the height of the content exceeds the height of the block

## 4.2.7.9. Profile - Subscription
- Reference mockup 'profile-subscription.png'
- Top bar remains same for all the profile screens
- Underneath it shows the switch to select between monthly and yearly billing cycle
- User "Yearly" label it should show the savings against monthly in percent for `Ultra` subscription
- Underneath shows the blocks for each plan
- Plan block shows the header and the name of the plan in the header
- Then list of the features offered in that plan
- And price for the plan under the feature list
- At the bottom shows "SELECT" button that allows user to select that plan as their subscription
- For the active subscription plan, in place of button should show "SELECTED" ina button like element
- The block is scrollable

## 4.2.7.10. Support
- Reference mockup 'support.png'
- Top bar is similar to home screen (4.2.7.1.)
- Below that the block to show all the support histories
- The block shows the title `SUPPORT HISTORY` on top of the block
- Below that it shows the list of all the historical chats
- In the list it'll only show the title and the date. The list item will be shown as bordered block with rounded corners
- The list block becomes scrollable if the content of the block have axceeded in height than the height of the block
- Underneath, on bottom right corner shows the message icon with 3 dots
- Tapping the message icon will slide-in a floating block that will show three options, `VIDEO CALL`, `VOICE CALL`, `CHAT`
- The options in the floating block will be inactive in the user plan doesn't have that feature or user has exhausted the limit for the feature
- Tapping the feature will open the relevant screen for support chat and persona (coordinator) for the user will continue chat
- The each screen for support will same learning. `VIDEO CALL` (4.2.7.3.), `VOICE CALL` (4.2.7.2.), `CHAT` (4.2.7.4.)


## 5. Feature Extension 1
- Create admin console frontend for admin functions
- All the functionality in admin specification (4.1.) shall be in admin console frontend
- Every sub-points (like 4.1.1., 4.1.2., 4.1.3. etc.) in admin specification (4.1.) should be the menu item and that feature should be configured from there
- Use tailwind css and reactjs for frontend

## 6. Feature Extension 2
- The `Roles` tab in admin right now only allowing permission for a complete feature. But permissions must be broken down to each action
- `manage_languages` should have sub-item for permission: 'add', 'edit', 'view', 'delete'
- `manage_admins` should have sub-item for permission: 'add', 'edit', 'view', 'delete'
- `manage_personas` should have sub-item for permission: 'add', 'edit', 'view', 'delete'
- `manage_users` should have sub-item for permission: 'add', 'edit', 'view', 'delete'
- If 'add' or 'edit' or 'delete' selected, 'view' will be selected automatically
- If 'view' is unselected all other will be unselected automatically
- If 'view' permission is no available for feature for any role then the Menu Item for that feature will not show in admin console when someone with the same role logs in
- At-least one role must be there will all the access and one user must be there with that role. Deleting such last one will not be possible
- New permission rules should be updated for entire admin console feature access

## 7. Feature Extension 3
- Bug Fix: In frontend Language list is not showing the flag despite the flag upload
- In persona, currenly teaching style is configured for a persona. But each persona will be able to teach in any style. It's the user who will select during onboarding in which style they want to learn
- Under plan, free plan is currently showing as unlimited video call, but free plan will have no video call
- For free plan make the video call is also configurable
- For all the plan and all the features value -1 will be considered "Not Available"
- Bug Fix: For agentic and coordinator support, 0 should mean unlimited but currently it's showing undefined. Fix it in frontend display and also in backend logic
- For plans, agentic and coordinator support value defines allowed minutes per month. Update frontend label and backend logic accordingly
- For plans, voice call, video call and text learning values are in minutes per day. Update frontend label and backend logic accordingly
- Bug Fix: For personas after upload the image of the persona is not showing in the admin console

## 8. Feature Extension 4
- Bug Fix: In admin frontend, language icon still not showing in language list page
- Bug Fix: In admin frontend, persona image is not showing in persona list page
