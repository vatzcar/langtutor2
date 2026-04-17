# Plan 3: Flutter App Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Flutter mobile app foundation — project setup, theming (pastel colors with bubble backgrounds), authentication via social login, Riverpod state management, navigation shell with bottom nav bar, and the home screen with language popup.

**Architecture:** Flutter app using Riverpod for state management, Dio for HTTP, GoRouter for navigation. Screens are organized by feature. Reusable widgets extracted for bottom nav, top info bar, persona avatars, and bubble backgrounds.

**Tech Stack:** Flutter 3.22+, Riverpod (flutter_riverpod + riverpod_annotation), Dio, GoRouter, google_sign_in, sign_in_with_apple, livekit_client, cached_network_image

---

### Task 1: Flutter Project Setup

**Files:**
- Create: `mobile/pubspec.yaml`
- Create: `mobile/lib/main.dart`
- Create: `mobile/lib/app.dart`
- Create: `mobile/lib/config/constants.dart`

- [ ] **Step 1: Create Flutter project**

```bash
cd "C:\Users\Vatzcar\Documents\LangTutorv2"
flutter create --org com.langtutor --project-name langtutor mobile
```

- [ ] **Step 2: Update pubspec.yaml with dependencies**

```yaml
# mobile/pubspec.yaml
name: langtutor
description: AI Language Tutor
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.4.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5
  dio: ^5.4.3
  go_router: ^14.2.0
  google_sign_in: ^6.2.1
  sign_in_with_apple: ^6.1.0
  livekit_client: ^2.1.5
  cached_network_image: ^3.3.1
  flutter_svg: ^2.0.10
  shared_preferences: ^2.2.3
  intl: ^0.19.0
  json_annotation: ^4.9.0
  freezed_annotation: ^2.4.1
  flutter_animate: ^4.5.0
  shimmer: ^3.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0
  build_runner: ^2.4.9
  json_serializable: ^6.8.0
  freezed: ^2.5.2
  riverpod_generator: ^2.4.0
  mockito: ^5.4.4
  mocktail: ^1.0.3

flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/fonts/
```

- [ ] **Step 3: Create constants**

```dart
// mobile/lib/config/constants.dart
class AppConstants {
  static const String apiBaseUrl = 'http://10.0.2.2:8000/api'; // Android emulator
  static const String livekitUrl = 'ws://10.0.2.2:7880';
  static const Duration tokenExpiry = Duration(hours: 24);
  static const int chatAutoScrollDelay = 5; // seconds for unread mark
}
```

- [ ] **Step 4: Create main.dart**

```dart
// mobile/lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: LangTutorApp()));
}
```

- [ ] **Step 5: Commit**

```bash
cd mobile && git add . && git commit -m "feat: scaffold Flutter project with dependencies"
```

---

### Task 2: Theme & Bubble Background

**Files:**
- Create: `mobile/lib/config/theme.dart`
- Create: `mobile/lib/widgets/bubble_background.dart`

- [ ] **Step 1: Create pastel color theme**

```dart
// mobile/lib/config/theme.dart
import 'package:flutter/material.dart';

class AppColors {
  // Primary pastel palette — casual/fun but eye-pleasing
  static const Color primary = Color(0xFF7C9FE5);       // Soft blue
  static const Color primaryLight = Color(0xFFB3D1FF);   // Light blue
  static const Color secondary = Color(0xFFE8A0BF);      // Soft pink
  static const Color accent = Color(0xFFFFD36E);          // Warm yellow
  static const Color success = Color(0xFF8ED1A5);         // Soft green
  static const Color error = Color(0xFFE88B8B);           // Soft red

  // Backgrounds — each screen gets a different pastel bg
  static const Color bgHome = Color(0xFFF0F4FF);         // Very light blue
  static const Color bgLearning = Color(0xFFF5F0FF);     // Very light purple
  static const Color bgPractice = Color(0xFFF0FFF4);     // Very light green
  static const Color bgProfile = Color(0xFFFFF5F0);      // Very light peach
  static const Color bgSupport = Color(0xFFFFF0F5);      // Very light pink
  static const Color bgChat = Color(0xFFFFFDF0);         // Very light cream
  static const Color bgOnboarding = Color(0xFFF0FAFF);   // Very light cyan

  // Neutrals
  static const Color textPrimary = Color(0xFF2D3142);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textMuted = Color(0xFF9CA3AF);
  static const Color disabled = Color(0xFFBDBDBD);
  static const Color disabledBg = Color(0xFFE0E0E0);
  static const Color cardBg = Color(0xFFFFFFFF);
  static const Color divider = Color(0xFFE5E7EB);

  // Bottom nav
  static const Color navBg = Color(0xFF3D4260);
  static const Color navActive = Color(0xFFFFD36E);
  static const Color navInactive = Color(0xFF9CA3AF);
}

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Nunito',
      colorScheme: ColorScheme.light(
        primary: AppColors.primary,
        secondary: AppColors.secondary,
        surface: AppColors.cardBg,
        error: AppColors.error,
      ),
      scaffoldBackgroundColor: AppColors.bgHome,
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
        headlineMedium: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
        headlineSmall: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
        bodyLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w500, color: AppColors.textPrimary),
        bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w400, color: AppColors.textSecondary),
        bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.w400, color: AppColors.textMuted),
        labelLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        color: AppColors.cardBg,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: AppColors.divider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: AppColors.divider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: AppColors.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.navBg,
        selectedItemColor: AppColors.navActive,
        unselectedItemColor: AppColors.navInactive,
        type: BottomNavigationBarType.fixed,
        showSelectedLabels: false,
        showUnselectedLabels: false,
      ),
    );
  }
}
```

- [ ] **Step 2: Create bubble background widget**

```dart
// mobile/lib/widgets/bubble_background.dart
import 'dart:math';
import 'package:flutter/material.dart';

class BubbleBackground extends StatelessWidget {
  final Color backgroundColor;
  final Widget child;

  const BubbleBackground({
    super.key,
    required this.backgroundColor,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Background color
        Container(color: backgroundColor),
        // Bubbles overlay
        CustomPaint(
          size: MediaQuery.of(context).size,
          painter: _BubblePainter(baseColor: backgroundColor),
        ),
        // Content
        child,
      ],
    );
  }
}

class _BubblePainter extends CustomPainter {
  final Color baseColor;
  final Random _random = Random(42); // Fixed seed for consistent bubbles

  _BubblePainter({required this.baseColor});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.fill;

    // Generate 12 subtle bubbles
    for (int i = 0; i < 12; i++) {
      final x = _random.nextDouble() * size.width;
      final y = _random.nextDouble() * size.height;
      final radius = 20.0 + _random.nextDouble() * 80;
      final opacity = 0.03 + _random.nextDouble() * 0.06;

      paint.color = Colors.white.withOpacity(opacity);
      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/config/ mobile/lib/widgets/
git commit -m "feat: add pastel theme and bubble background widget"
```

---

### Task 3: Data Models

**Files:**
- Create: `mobile/lib/models/user.dart`
- Create: `mobile/lib/models/language.dart`
- Create: `mobile/lib/models/persona.dart`
- Create: `mobile/lib/models/plan.dart`
- Create: `mobile/lib/models/subscription.dart`
- Create: `mobile/lib/models/session.dart`
- Create: `mobile/lib/models/chat_message.dart`
- Create: `mobile/lib/models/cefr_level.dart`

- [ ] **Step 1: Create all data models**

```dart
// mobile/lib/models/user.dart
class User {
  final String id;
  final String email;
  final String name;
  final String? dateOfBirth;
  final String? avatarId;
  final String? nativeLanguageId;
  final bool isActive;
  final bool isBanned;

  User({
    required this.id,
    required this.email,
    required this.name,
    this.dateOfBirth,
    this.avatarId,
    this.nativeLanguageId,
    this.isActive = true,
    this.isBanned = false,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'],
    email: json['email'],
    name: json['name'],
    dateOfBirth: json['date_of_birth'],
    avatarId: json['avatar_id'],
    nativeLanguageId: json['native_language_id'],
    isActive: json['is_active'] ?? true,
    isBanned: json['is_banned'] ?? false,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'name': name,
    'date_of_birth': dateOfBirth,
    'avatar_id': avatarId,
    'native_language_id': nativeLanguageId,
  };
}
```

```dart
// mobile/lib/models/language.dart
class Language {
  final String id;
  final String name;
  final String locale;
  final String? iconUrl;
  final bool isDefault;
  final bool isFallback;
  final bool isActive;

  Language({
    required this.id,
    required this.name,
    required this.locale,
    this.iconUrl,
    this.isDefault = false,
    this.isFallback = false,
    this.isActive = true,
  });

  factory Language.fromJson(Map<String, dynamic> json) => Language(
    id: json['id'],
    name: json['name'],
    locale: json['locale'],
    iconUrl: json['icon_url'],
    isDefault: json['is_default'] ?? false,
    isFallback: json['is_fallback'] ?? false,
    isActive: json['is_active'] ?? true,
  );
}
```

```dart
// mobile/lib/models/persona.dart
class Persona {
  final String id;
  final String name;
  final String languageId;
  final String? imageUrl;
  final String gender;
  final String type; // teacher, coordinator, peer
  final String? teachingStyle;
  final bool isActive;

  Persona({
    required this.id,
    required this.name,
    required this.languageId,
    this.imageUrl,
    required this.gender,
    required this.type,
    this.teachingStyle,
    this.isActive = true,
  });

  factory Persona.fromJson(Map<String, dynamic> json) => Persona(
    id: json['id'],
    name: json['name'],
    languageId: json['language_id'],
    imageUrl: json['image_url'],
    gender: json['gender'],
    type: json['type'],
    teachingStyle: json['teaching_style'],
    isActive: json['is_active'] ?? true,
  );
}
```

```dart
// mobile/lib/models/plan.dart
class Plan {
  final String id;
  final String name;
  final String slug;
  final double priceMonthly;
  final double priceYearly;
  final int textLearningLimitMinutes;
  final int voiceCallLimitMinutes;
  final int videoCallLimitMinutes;
  final int agenticVoiceLimitMonthly;
  final int coordinatorVideoLimitMonthly;

  Plan({
    required this.id,
    required this.name,
    required this.slug,
    required this.priceMonthly,
    required this.priceYearly,
    this.textLearningLimitMinutes = 0,
    this.voiceCallLimitMinutes = 0,
    this.videoCallLimitMinutes = 0,
    this.agenticVoiceLimitMonthly = 0,
    this.coordinatorVideoLimitMonthly = 0,
  });

  factory Plan.fromJson(Map<String, dynamic> json) => Plan(
    id: json['id'],
    name: json['name'],
    slug: json['slug'],
    priceMonthly: (json['price_monthly'] as num).toDouble(),
    priceYearly: (json['price_yearly'] as num).toDouble(),
    textLearningLimitMinutes: json['text_learning_limit_minutes'] ?? 0,
    voiceCallLimitMinutes: json['voice_call_limit_minutes'] ?? 0,
    videoCallLimitMinutes: json['video_call_limit_minutes'] ?? 0,
    agenticVoiceLimitMonthly: json['agentic_voice_limit_monthly'] ?? 0,
    coordinatorVideoLimitMonthly: json['coordinator_video_limit_monthly'] ?? 0,
  );

  bool get hasVoiceCall => voiceCallLimitMinutes != 0 || slug != 'free';
  bool get hasVideoCall => videoCallLimitMinutes != 0;
  bool get isUnlimitedVoice => voiceCallLimitMinutes == 0 && slug != 'free';
  bool get isUnlimitedVideo => videoCallLimitMinutes == 0 && slug == 'ultra';

  double get yearlySavings {
    if (priceYearly <= 0 || priceMonthly <= 0) return 0;
    return ((priceMonthly * 12 - priceYearly) / (priceMonthly * 12)) * 100;
  }
}
```

```dart
// mobile/lib/models/subscription.dart
class Subscription {
  final String id;
  final String userId;
  final String planId;
  final String billingCycle;
  final String startedAt;
  final String? expiresAt;
  final bool isActive;

  Subscription({
    required this.id,
    required this.userId,
    required this.planId,
    required this.billingCycle,
    required this.startedAt,
    this.expiresAt,
    this.isActive = true,
  });

  factory Subscription.fromJson(Map<String, dynamic> json) => Subscription(
    id: json['id'],
    userId: json['user_id'],
    planId: json['plan_id'],
    billingCycle: json['billing_cycle'],
    startedAt: json['started_at'],
    expiresAt: json['expires_at'],
    isActive: json['is_active'] ?? true,
  );
}
```

```dart
// mobile/lib/models/session.dart
class LearningSession {
  final String id;
  final String sessionType;
  final String sessionMode;
  final int durationSeconds;
  final String? cefrLevelAtTime;
  final String startedAt;
  final String? endedAt;

  LearningSession({
    required this.id,
    required this.sessionType,
    required this.sessionMode,
    this.durationSeconds = 0,
    this.cefrLevelAtTime,
    required this.startedAt,
    this.endedAt,
  });

  factory LearningSession.fromJson(Map<String, dynamic> json) => LearningSession(
    id: json['id'],
    sessionType: json['session_type'],
    sessionMode: json['session_mode'],
    durationSeconds: json['duration_seconds'] ?? 0,
    cefrLevelAtTime: json['cefr_level_at_time'],
    startedAt: json['started_at'],
    endedAt: json['ended_at'],
  );
}
```

```dart
// mobile/lib/models/chat_message.dart
class ChatMessage {
  final String id;
  final String sender; // user, persona
  final String content;
  final bool isRead;
  final String createdAt;

  ChatMessage({
    required this.id,
    required this.sender,
    required this.content,
    this.isRead = false,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
    id: json['id'],
    sender: json['sender'],
    content: json['content'],
    isRead: json['is_read'] ?? false,
    createdAt: json['created_at'],
  );
}
```

```dart
// mobile/lib/models/cefr_level.dart
class CefrLevelInfo {
  final String level;
  final String status; // passed, in_progress
  final int lessonsCount;
  final double hoursSpent;
  final int streakDays;
  final double progressPercent;
  final int practiceSessions;
  final double practiceHours;

  CefrLevelInfo({
    required this.level,
    required this.status,
    this.lessonsCount = 0,
    this.hoursSpent = 0,
    this.streakDays = 0,
    this.progressPercent = 0,
    this.practiceSessions = 0,
    this.practiceHours = 0,
  });

  factory CefrLevelInfo.fromJson(Map<String, dynamic> json) => CefrLevelInfo(
    level: json['cefr_level'],
    status: json['status'],
    lessonsCount: json['lessons_count'] ?? 0,
    hoursSpent: (json['hours_spent'] as num?)?.toDouble() ?? 0,
    streakDays: json['streak_days'] ?? 0,
    progressPercent: (json['progress_percent'] as num?)?.toDouble() ?? 0,
    practiceSessions: json['practice_sessions'] ?? 0,
    practiceHours: (json['practice_hours'] as num?)?.toDouble() ?? 0,
  );
}

class UserLanguageInfo {
  final String id;
  final String languageId;
  final String? teacherPersonaId;
  final String? teachingStyle;
  final String currentCefrLevel;
  final double cefrProgressPercent;

  UserLanguageInfo({
    required this.id,
    required this.languageId,
    this.teacherPersonaId,
    this.teachingStyle,
    required this.currentCefrLevel,
    this.cefrProgressPercent = 0,
  });

  factory UserLanguageInfo.fromJson(Map<String, dynamic> json) => UserLanguageInfo(
    id: json['id'],
    languageId: json['language_id'],
    teacherPersonaId: json['teacher_persona_id'],
    teachingStyle: json['teaching_style'],
    currentCefrLevel: json['current_cefr_level'],
    cefrProgressPercent: (json['cefr_progress_percent'] as num?)?.toDouble() ?? 0,
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/models/
git commit -m "feat: add Flutter data models for all entities"
```

---

### Task 4: API Client & Auth Service

**Files:**
- Create: `mobile/lib/services/api_client.dart`
- Create: `mobile/lib/services/auth_service.dart`
- Create: `mobile/lib/providers/auth_provider.dart`

- [ ] **Step 1: Create Dio API client**

```dart
// mobile/lib/services/api_client.dart
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/constants.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConstants.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final prefs = await SharedPreferences.getInstance();
        final token = prefs.getString('access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          // Token expired — trigger logout
        }
        return handler.next(error);
      },
    ));
  }

  Dio get dio => _dio;

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _dio.get(path, queryParameters: queryParameters);

  Future<Response> post(String path, {dynamic data}) =>
      _dio.post(path, data: data);

  Future<Response> patch(String path, {dynamic data}) =>
      _dio.patch(path, data: data);

  Future<Response> delete(String path) => _dio.delete(path);
}
```

- [ ] **Step 2: Create auth service with social login**

```dart
// mobile/lib/services/auth_service.dart
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';

class AuthService {
  final ApiClient _api;
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: ['email', 'profile']);

  AuthService(this._api);

  Future<Map<String, dynamic>> signInWithGoogle() async {
    final account = await _googleSignIn.signIn();
    if (account == null) throw Exception('Google sign-in cancelled');

    final auth = await account.authentication;
    final idToken = auth.idToken;
    if (idToken == null) throw Exception('No Google ID token');

    return _authenticateWithBackend('google', idToken);
  }

  Future<Map<String, dynamic>> signInWithApple() async {
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [AppleIDAuthorizationScopes.email, AppleIDAuthorizationScopes.fullName],
    );

    final idToken = credential.identityToken;
    if (idToken == null) throw Exception('No Apple ID token');

    return _authenticateWithBackend('apple', idToken);
  }

  Future<Map<String, dynamic>> _authenticateWithBackend(String provider, String idToken) async {
    final response = await _api.post('/auth/social-login', data: {
      'provider': provider,
      'id_token': idToken,
    });

    final data = response.data;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', data['access_token']);
    await prefs.setString('user_id', data['user_id']);

    return data;
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('user_id');
  }

  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey('access_token');
  }
}
```

- [ ] **Step 3: Create auth provider**

```dart
// mobile/lib/providers/auth_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../models/user.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref.read(apiClientProvider));
});

enum AuthStatus { initial, authenticated, unauthenticated, onboarding }

class AuthState {
  final AuthStatus status;
  final User? user;
  final bool isNewUser;
  final String? error;

  AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.isNewUser = false,
    this.error,
  });

  AuthState copyWith({AuthStatus? status, User? user, bool? isNewUser, String? error}) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      isNewUser: isNewUser ?? this.isNewUser,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final ApiClient _apiClient;

  AuthNotifier(this._authService, this._apiClient) : super(AuthState()) {
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final loggedIn = await _authService.isLoggedIn();
    if (loggedIn) {
      try {
        final resp = await _apiClient.get('/mobile/users/me');
        final user = User.fromJson(resp.data);
        state = state.copyWith(status: AuthStatus.authenticated, user: user);
      } catch (e) {
        state = state.copyWith(status: AuthStatus.unauthenticated);
      }
    } else {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> signInWithGoogle() async {
    try {
      final data = await _authService.signInWithGoogle();
      final resp = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(resp.data);
      // Check if user needs onboarding (no native language set)
      final needsOnboarding = user.nativeLanguageId == null;
      state = state.copyWith(
        status: needsOnboarding ? AuthStatus.onboarding : AuthStatus.authenticated,
        user: user,
        isNewUser: needsOnboarding,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> signInWithApple() async {
    try {
      final data = await _authService.signInWithApple();
      final resp = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(resp.data);
      final needsOnboarding = user.nativeLanguageId == null;
      state = state.copyWith(
        status: needsOnboarding ? AuthStatus.onboarding : AuthStatus.authenticated,
        user: user,
        isNewUser: needsOnboarding,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> completeOnboarding() async {
    final resp = await _apiClient.get('/mobile/users/me');
    final user = User.fromJson(resp.data);
    state = state.copyWith(status: AuthStatus.authenticated, user: user, isNewUser: false);
  }

  Future<void> signOut() async {
    await _authService.signOut();
    state = AuthState(status: AuthStatus.unauthenticated);
  }

  Future<void> refreshUser() async {
    try {
      final resp = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(resp.data);
      state = state.copyWith(user: user);
    } catch (_) {}
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(authServiceProvider), ref.read(apiClientProvider));
});
```

- [ ] **Step 4: Commit**

```bash
git add mobile/lib/services/ mobile/lib/providers/
git commit -m "feat: add API client, auth service, and auth state management"
```

---

### Task 5: Navigation & App Shell

**Files:**
- Create: `mobile/lib/config/routes.dart`
- Create: `mobile/lib/widgets/bottom_nav_bar.dart`
- Create: `mobile/lib/widgets/top_info_bar.dart`
- Modify: `mobile/lib/app.dart`

- [ ] **Step 1: Create bottom navigation bar**

```dart
// mobile/lib/widgets/bottom_nav_bar.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';

class AppBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const AppBottomNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.navBg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, -2)),
        ],
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _NavItem(icon: Icons.home_rounded, label: 'Home', isActive: currentIndex == 0, onTap: () => onTap(0)),
              _NavItem(icon: Icons.fitness_center_rounded, label: 'Practice', isActive: currentIndex == 1, onTap: () => onTap(1)),
              _NavItem(icon: Icons.person_rounded, label: 'Profile', isActive: currentIndex == 2, onTap: () => onTap(2)),
              _NavItem(icon: Icons.support_agent_rounded, label: 'Support', isActive: currentIndex == 3, onTap: () => onTap(3)),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _NavItem({required this.icon, required this.label, required this.isActive, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: isActive ? AppColors.navActive : AppColors.navInactive, size: 28),
            const SizedBox(height: 2),
            Container(
              width: 4, height: 4,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isActive ? AppColors.navActive : Colors.transparent,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Create top info bar**

```dart
// mobile/lib/widgets/top_info_bar.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';

class TopInfoBar extends StatelessWidget {
  final String? languageFlag;
  final String cefrLevel;
  final double progressPercent;
  final String planName;
  final VoidCallback? onLanguageTap;

  const TopInfoBar({
    super.key,
    this.languageFlag,
    required this.cefrLevel,
    required this.progressPercent,
    required this.planName,
    this.onLanguageTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          // Language flag
          GestureDetector(
            onTap: onLanguageTap,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.navBg,
                borderRadius: BorderRadius.circular(8),
              ),
              child: languageFlag != null
                  ? Image.network(languageFlag!, width: 24, height: 18, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(Icons.flag, color: Colors.white, size: 18))
                  : const Icon(Icons.flag, color: Colors.white, size: 18),
            ),
          ),
          const SizedBox(width: 12),

          // CEFR Level
          Text(cefrLevel, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(width: 8),

          // Progress
          Text('${progressPercent.toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.textMuted)),

          const Spacer(),

          // Plan name
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.accent.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(planName, style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w700, color: AppColors.textPrimary,
            )),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Create GoRouter configuration**

```dart
// mobile/lib/config/routes.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/practice/practice_hub_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/support/support_screen.dart';
import '../screens/onboarding/onboarding_call_screen.dart';
import '../screens/onboarding/user_info_screen.dart';
import '../screens/onboarding/plan_selection_screen.dart';
import '../screens/learning/voice_call_screen.dart';
import '../screens/learning/video_call_screen.dart';
import '../screens/learning/chat_screen.dart';
import '../screens/profile/cefr_screen.dart';
import '../screens/profile/history_screen.dart';
import '../screens/profile/subscription_screen.dart';
import '../screens/profile/profile_edit_screen.dart';
import '../screens/profile/transcript_screen.dart';
import '../widgets/bottom_nav_bar.dart';
import '../widgets/bubble_background.dart';
import 'theme.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    redirect: (context, state) {
      final isLoggedIn = authState.status == AuthStatus.authenticated;
      final isOnboarding = authState.status == AuthStatus.onboarding;
      final isLoginRoute = state.matchedLocation == '/login';
      final isOnboardingRoute = state.matchedLocation.startsWith('/onboarding');

      if (authState.status == AuthStatus.initial) return null;
      if (!isLoggedIn && !isOnboarding && !isLoginRoute) return '/login';
      if (isLoggedIn && isLoginRoute) return '/home';
      if (isOnboarding && !isOnboardingRoute) return '/onboarding';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),

      // Onboarding routes
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingCallScreen()),
      GoRoute(path: '/onboarding/info', builder: (_, __) => const UserInfoScreen()),
      GoRoute(path: '/onboarding/plan', builder: (_, __) => const PlanSelectionScreen()),

      // Shell route with bottom nav
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => _AppShell(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/practice', builder: (_, __) => const PracticeHubScreen()),
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          GoRoute(path: '/support', builder: (_, __) => const SupportScreen()),
        ],
      ),

      // Full-screen routes (no bottom nav)
      GoRoute(path: '/learning/voice', builder: (_, state) => VoiceCallScreen(mode: state.extra as String? ?? 'learning')),
      GoRoute(path: '/learning/video', builder: (_, state) => VideoCallScreen(mode: state.extra as String? ?? 'learning')),
      GoRoute(path: '/learning/chat', builder: (_, state) => ChatScreen(mode: state.extra as String? ?? 'learning')),
      GoRoute(path: '/profile/cefr', builder: (_, __) => const CefrScreen()),
      GoRoute(path: '/profile/history', builder: (_, __) => const HistoryScreen()),
      GoRoute(path: '/profile/subscription', builder: (_, __) => const SubscriptionScreen()),
      GoRoute(path: '/profile/edit', builder: (_, __) => const ProfileEditScreen()),
      GoRoute(path: '/profile/transcript/:sessionId', builder: (_, state) =>
          TranscriptScreen(sessionId: state.pathParameters['sessionId']!)),
    ],
  );
});

class _AppShell extends StatefulWidget {
  final Widget child;
  const _AppShell({required this.child});

  @override
  State<_AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<_AppShell> {
  int _currentIndex = 0;

  static const _routes = ['/home', '/practice', '/profile', '/support'];
  static const _bgColors = [AppColors.bgHome, AppColors.bgPractice, AppColors.bgProfile, AppColors.bgSupport];

  @override
  Widget build(BuildContext context) {
    // Sync index with current route
    final location = GoRouterState.of(context).matchedLocation;
    _currentIndex = _routes.indexOf(location).clamp(0, 3);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: _bgColors[_currentIndex],
        child: SafeArea(child: widget.child),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
          context.go(_routes[index]);
        },
      ),
    );
  }
}
```

- [ ] **Step 4: Create app.dart with router**

```dart
// mobile/lib/app.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/theme.dart';
import 'config/routes.dart';

class LangTutorApp extends ConsumerWidget {
  const LangTutorApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'LangTutor',
      theme: AppTheme.lightTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/
git commit -m "feat: add navigation shell with GoRouter, bottom nav bar, and top info bar"
```

---

### Task 6: Login Screen

**Files:**
- Create: `mobile/lib/screens/auth/login_screen.dart`

- [ ] **Step 1: Implement login screen**

```dart
// mobile/lib/screens/auth/login_screen.dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/bubble_background.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(flex: 2),

                // Logo / Brand
                Container(
                  width: 120, height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [AppColors.primary, AppColors.secondary],
                      begin: Alignment.topLeft, end: Alignment.bottomRight,
                    ),
                  ),
                  child: const Icon(Icons.translate_rounded, size: 56, color: Colors.white),
                ),
                const SizedBox(height: 24),

                Text('LangTutor', style: Theme.of(context).textTheme.headlineLarge),
                const SizedBox(height: 8),
                Text('Learn languages with AI', style: Theme.of(context).textTheme.bodyMedium),

                const Spacer(),

                // Error message
                if (authState.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(authState.error!, style: TextStyle(color: AppColors.error)),
                  ),

                // Google Sign In
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => ref.read(authProvider.notifier).signInWithGoogle(),
                    icon: const Icon(Icons.g_mobiledata, size: 24),
                    label: const Text('Continue with Google'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppColors.textPrimary,
                      side: BorderSide(color: AppColors.divider),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Apple Sign In (iOS only)
                if (Platform.isIOS)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => ref.read(authProvider.notifier).signInWithApple(),
                      icon: const Icon(Icons.apple, size: 24),
                      label: const Text('Continue with Apple'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.black,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),

                const Spacer(flex: 2),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/auth/
git commit -m "feat: add login screen with Google and Apple social login"
```

---

### Task 7: Home Screen & Language Popup

**Files:**
- Create: `mobile/lib/screens/home/home_screen.dart`
- Create: `mobile/lib/screens/home/language_popup.dart`
- Create: `mobile/lib/providers/language_provider.dart`
- Create: `mobile/lib/providers/user_provider.dart`
- Create: `mobile/lib/widgets/persona_avatar.dart`

- [ ] **Step 1: Create language and user providers**

```dart
// mobile/lib/providers/language_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/language.dart';
import '../models/cefr_level.dart';
import 'auth_provider.dart';

final languagesProvider = FutureProvider<List<Language>>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/languages');
  return (resp.data as List).map((e) => Language.fromJson(e)).toList();
});

final userLanguagesProvider = FutureProvider<List<UserLanguageInfo>>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/users/me/languages');
  return (resp.data as List).map((e) => UserLanguageInfo.fromJson(e)).toList();
});

final selectedLanguageProvider = StateProvider<UserLanguageInfo?>((ref) => null);
```

```dart
// mobile/lib/providers/user_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/plan.dart';
import '../models/subscription.dart';
import 'auth_provider.dart';

final currentSubscriptionProvider = FutureProvider<Subscription?>((ref) async {
  final api = ref.read(apiClientProvider);
  try {
    final resp = await api.get('/mobile/subscriptions/current');
    return resp.data != null ? Subscription.fromJson(resp.data) : null;
  } catch (_) {
    return null;
  }
});

final plansProvider = FutureProvider<List<Plan>>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/plans');
  return (resp.data as List).map((e) => Plan.fromJson(e)).toList();
});

final currentPlanProvider = FutureProvider<Plan?>((ref) async {
  final sub = await ref.watch(currentSubscriptionProvider.future);
  final plans = await ref.watch(plansProvider.future);
  if (sub == null) return plans.firstWhere((p) => p.slug == 'free');
  return plans.firstWhere((p) => p.id == sub.planId, orElse: () => plans.first);
});

final usageCheckProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, feature) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/sessions/usage/check', queryParameters: {'feature': feature});
  return resp.data;
});
```

- [ ] **Step 2: Create persona avatar widget**

```dart
// mobile/lib/widgets/persona_avatar.dart
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../config/theme.dart';

class PersonaAvatar extends StatelessWidget {
  final String? imageUrl;
  final double size;
  final bool showBorder;

  const PersonaAvatar({
    super.key,
    this.imageUrl,
    this.size = 200,
    this.showBorder = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: showBorder ? Border.all(color: AppColors.primary.withOpacity(0.3), width: 3) : null,
        boxShadow: [
          BoxShadow(color: AppColors.primary.withOpacity(0.15), blurRadius: 20, spreadRadius: 2),
        ],
      ),
      child: ClipOval(
        child: imageUrl != null
            ? CachedNetworkImage(
                imageUrl: imageUrl!,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(
                  color: AppColors.disabledBg,
                  child: Icon(Icons.person, size: size * 0.5, color: AppColors.disabled),
                ),
                errorWidget: (_, __, ___) => Container(
                  color: AppColors.disabledBg,
                  child: Icon(Icons.person, size: size * 0.5, color: AppColors.disabled),
                ),
              )
            : Container(
                color: AppColors.disabledBg,
                child: Icon(Icons.person, size: size * 0.5, color: AppColors.disabled),
              ),
      ),
    );
  }
}
```

- [ ] **Step 3: Create home screen**

```dart
// mobile/lib/screens/home/home_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/top_info_bar.dart';
import '../../widgets/persona_avatar.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';
import 'language_popup.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final selectedLang = ref.watch(selectedLanguageProvider);
    final planAsync = ref.watch(currentPlanProvider);

    return Column(
      children: [
        // Top Info Bar
        TopInfoBar(
          cefrLevel: selectedLang?.currentCefrLevel ?? 'A0',
          progressPercent: selectedLang?.cefrProgressPercent ?? 0,
          planName: planAsync.whenOrNull(data: (plan) => plan?.name) ?? 'Free',
          onLanguageTap: () => _showLanguagePopup(context, ref),
        ),

        const Spacer(),

        // Profile image / persona
        PersonaAvatar(
          imageUrl: authState.user?.avatarId != null ? null : null, // Will resolve from API
          size: 220,
        ),

        const Spacer(),

        // Call buttons
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              decoration: BoxDecoration(
                color: AppColors.navBg,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  // Voice call
                  _CallButton(
                    icon: Icons.phone,
                    onTap: () => context.push('/learning/voice', extra: 'learning'),
                    enabled: planAsync.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false,
                  ),
                  Container(width: 1, height: 50, color: Colors.white24),
                  // Video call
                  _CallButton(
                    icon: Icons.videocam,
                    onTap: () => context.push('/learning/video', extra: 'learning'),
                    enabled: planAsync.whenOrNull(data: (p) => p?.hasVideoCall) ?? false,
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Chat button
        SizedBox(
          width: 200,
          child: ElevatedButton(
            onPressed: () => context.push('/learning/chat', extra: 'learning'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.navBg,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: const Text('CHAT', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, letterSpacing: 2)),
          ),
        ),

        const Spacer(flex: 2),
      ],
    );
  }

  void _showLanguagePopup(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      barrierColor: Colors.black54,
      builder: (_) => const LanguagePopup(),
    );
  }
}

class _CallButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  final bool enabled;

  const _CallButton({required this.icon, this.onTap, required this.enabled});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        child: Icon(
          icon,
          size: 36,
          color: enabled ? Colors.white : AppColors.disabled,
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Create language popup**

```dart
// mobile/lib/screens/home/language_popup.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../providers/language_provider.dart';
import '../../models/language.dart';
import '../../models/cefr_level.dart';

class LanguagePopup extends ConsumerWidget {
  const LanguagePopup({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userLangsAsync = ref.watch(userLanguagesProvider);
    final allLangsAsync = ref.watch(languagesProvider);

    return GestureDetector(
      onTap: () => Navigator.of(context).pop(),
      child: Material(
        color: Colors.transparent,
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Prevent closing when tapping popup body
            child: Container(
              width: MediaQuery.of(context).size.width * 0.85,
              constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.7),
              decoration: BoxDecoration(
                color: AppColors.navBg.withOpacity(0.95),
                borderRadius: BorderRadius.circular(20),
              ),
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Currently learning languages
                  userLangsAsync.when(
                    data: (userLangs) {
                      return allLangsAsync.when(
                        data: (allLangs) {
                          final learningLangs = allLangs.where(
                            (l) => userLangs.any((ul) => ul.languageId == l.id),
                          ).toList();

                          final availableLangs = allLangs.where(
                            (l) => !userLangs.any((ul) => ul.languageId == l.id),
                          ).toList();

                          return Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              // Current languages row
                              Wrap(
                                spacing: 12,
                                runSpacing: 12,
                                children: learningLangs.map((lang) => _LanguageFlag(
                                  language: lang,
                                  onTap: () {
                                    final ul = userLangs.firstWhere((u) => u.languageId == lang.id);
                                    ref.read(selectedLanguageProvider.notifier).state = ul;
                                    Navigator.of(context).pop();
                                  },
                                )).toList(),
                              ),

                              if (availableLangs.isNotEmpty) ...[
                                const Padding(
                                  padding: EdgeInsets.symmetric(vertical: 16),
                                  child: Divider(color: Colors.white24),
                                ),
                                Text('Learn A New Language',
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white70)),
                                const SizedBox(height: 12),

                                // Available languages
                                Flexible(
                                  child: SingleChildScrollView(
                                    child: Wrap(
                                      spacing: 12,
                                      runSpacing: 12,
                                      children: availableLangs.map((lang) => _LanguageFlag(
                                        language: lang,
                                        onTap: () {
                                          Navigator.of(context).pop();
                                          // Start onboarding for new language
                                          context.push('/onboarding', extra: lang);
                                        },
                                      )).toList(),
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          );
                        },
                        loading: () => const CircularProgressIndicator(),
                        error: (_, __) => const Text('Error loading languages', style: TextStyle(color: Colors.white)),
                      );
                    },
                    loading: () => const CircularProgressIndicator(),
                    error: (_, __) => const Text('Error', style: TextStyle(color: Colors.white)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LanguageFlag extends StatelessWidget {
  final Language language;
  final VoidCallback onTap;

  const _LanguageFlag({required this.language, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white12,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (language.iconUrl != null)
              Image.network(language.iconUrl!, width: 24, height: 18,
                errorBuilder: (_, __, ___) => const Icon(Icons.flag, size: 18, color: Colors.white)),
            if (language.iconUrl == null)
              const Icon(Icons.flag, size: 18, color: Colors.white),
            const SizedBox(width: 8),
            Text(language.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/
git commit -m "feat: add home screen with language popup, persona avatar, and providers"
```

---

### Task 8: Onboarding Screens (Stub)

**Files:**
- Create: `mobile/lib/screens/onboarding/onboarding_call_screen.dart`
- Create: `mobile/lib/screens/onboarding/user_info_screen.dart`
- Create: `mobile/lib/screens/onboarding/plan_selection_screen.dart`
- Create: `mobile/lib/widgets/plan_card.dart`

- [ ] **Step 1: Create onboarding call screen (video call with coordinator)**

```dart
// mobile/lib/screens/onboarding/onboarding_call_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';

class OnboardingCallScreen extends ConsumerStatefulWidget {
  const OnboardingCallScreen({super.key});

  @override
  ConsumerState<OnboardingCallScreen> createState() => _OnboardingCallScreenState();
}

class _OnboardingCallScreenState extends ConsumerState<OnboardingCallScreen> {
  bool _isConnecting = true;

  @override
  void initState() {
    super.initState();
    _startOnboarding();
  }

  Future<void> _startOnboarding() async {
    // TODO: Connect to LiveKit room for onboarding
    // For now, simulate the connection
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) setState(() => _isConnecting = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(),
              if (_isConnecting)
                Column(
                  children: [
                    const CircularProgressIndicator(color: AppColors.primary),
                    const SizedBox(height: 16),
                    Text('Connecting to your coordinator...',
                        style: Theme.of(context).textTheme.bodyLarge),
                  ],
                )
              else
                Expanded(
                  child: Column(
                    children: [
                      // Video/Avatar area
                      Expanded(
                        flex: 3,
                        child: Container(
                          margin: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.navBg,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: const Center(
                            child: Text('Video Feed',
                                style: TextStyle(color: Colors.white54, fontSize: 18)),
                          ),
                        ),
                      ),

                      // Transcript area
                      Expanded(
                        flex: 2,
                        child: Container(
                          width: double.infinity,
                          margin: const EdgeInsets.symmetric(horizontal: 16),
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.navBg.withOpacity(0.8),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Text('Transcript will appear here...',
                              style: TextStyle(color: Colors.white70)),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // End call button
                      GestureDetector(
                        onTap: () => context.go('/onboarding/info'),
                        child: Container(
                          width: 64, height: 64,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppColors.error,
                          ),
                          child: const Icon(Icons.stop, color: Colors.white, size: 28),
                        ),
                      ),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Create user info screen**

```dart
// mobile/lib/screens/onboarding/user_info_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/bubble_background.dart';

class UserInfoScreen extends ConsumerStatefulWidget {
  const UserInfoScreen({super.key});

  @override
  ConsumerState<UserInfoScreen> createState() => _UserInfoScreenState();
}

class _UserInfoScreenState extends ConsumerState<UserInfoScreen> {
  final _nameController = TextEditingController();
  DateTime? _dateOfBirth;
  int _selectedAvatarIndex = 0;

  final List<String> _avatarPlaceholders = List.generate(8, (i) => 'Avatar ${i + 1}');

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),
                Center(child: Text('Tell us about yourself',
                    style: Theme.of(context).textTheme.headlineMedium)),
                const SizedBox(height: 32),

                // Name
                Text('Your Name', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 8),
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(hintText: 'Enter your name'),
                ),
                const SizedBox(height: 24),

                // Date of Birth
                Text('Date of Birth (optional)', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 8),
                GestureDetector(
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: DateTime(2000),
                      firstDate: DateTime(1920),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) setState(() => _dateOfBirth = date);
                  },
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.divider),
                    ),
                    child: Text(
                      _dateOfBirth != null
                          ? '${_dateOfBirth!.day}/${_dateOfBirth!.month}/${_dateOfBirth!.year}'
                          : 'Select date',
                      style: TextStyle(color: _dateOfBirth != null ? AppColors.textPrimary : AppColors.textMuted),
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Avatar selection
                Text('Choose Avatar', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 12),
                SizedBox(
                  height: 80,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _avatarPlaceholders.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 12),
                    itemBuilder: (_, index) => GestureDetector(
                      onTap: () => setState(() => _selectedAvatarIndex = index),
                      child: Container(
                        width: 72, height: 72,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.disabledBg,
                          border: Border.all(
                            color: _selectedAvatarIndex == index ? AppColors.primary : Colors.transparent,
                            width: 3,
                          ),
                        ),
                        child: Center(child: Icon(Icons.person, color: AppColors.disabled, size: 36)),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 40),

                // Continue button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _nameController.text.isNotEmpty ? () {
                      // TODO: Submit user info to API
                      context.go('/onboarding/plan');
                    } : null,
                    child: const Text('Continue'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: Create plan card widget**

```dart
// mobile/lib/widgets/plan_card.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/plan.dart';

class PlanCard extends StatelessWidget {
  final Plan plan;
  final bool isYearly;
  final bool isSelected;
  final VoidCallback onSelect;

  const PlanCard({
    super.key,
    required this.plan,
    required this.isYearly,
    this.isSelected = false,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final price = isYearly ? plan.priceYearly : plan.priceMonthly;
    final period = isYearly ? '/year' : '/month';

    final Color headerColor;
    switch (plan.slug) {
      case 'free':
        headerColor = AppColors.textMuted;
      case 'pro':
        headerColor = AppColors.primary;
      case 'ultra':
        headerColor = AppColors.secondary;
      default:
        headerColor = AppColors.textMuted;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: isSelected ? headerColor : AppColors.divider, width: 2),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 12),
            color: headerColor,
            child: Text(plan.name.toUpperCase(),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: 2)),
          ),

          // Features
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.white,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _feature('Unlimited text learning'),
                if (plan.voiceCallLimitMinutes > 0)
                  _feature('${plan.voiceCallLimitMinutes} min/day voice calls')
                else if (plan.slug != 'free')
                  _feature('Unlimited voice calls'),
                if (plan.videoCallLimitMinutes > 0)
                  _feature('${plan.videoCallLimitMinutes} min/day video calls')
                else if (plan.slug == 'ultra')
                  _feature('Unlimited video calls'),
                if (plan.agenticVoiceLimitMonthly > 0)
                  _feature('${plan.agenticVoiceLimitMonthly} support voice calls/month'),
                if (plan.coordinatorVideoLimitMonthly > 0)
                  _feature('${plan.coordinatorVideoLimitMonthly} coordinator video calls/month'),
                if (plan.slug == 'ultra')
                  _feature('Unlimited everything'),

                const SizedBox(height: 12),

                // Price
                Center(
                  child: Text(
                    price > 0 ? '\$${price.toStringAsFixed(2)}$period' : 'Free',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                  ),
                ),
                const SizedBox(height: 12),

                // Select button
                SizedBox(
                  width: double.infinity,
                  child: isSelected
                      ? Container(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          decoration: BoxDecoration(
                            color: headerColor.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text('SELECTED',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: headerColor, fontWeight: FontWeight.w700)),
                        )
                      : ElevatedButton(
                          onPressed: onSelect,
                          style: ElevatedButton.styleFrom(backgroundColor: headerColor),
                          child: const Text('SELECT'),
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _feature(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(Icons.check_circle, color: AppColors.success, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 14))),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: Create plan selection screen**

```dart
// mobile/lib/screens/onboarding/plan_selection_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/plan_card.dart';

class PlanSelectionScreen extends ConsumerStatefulWidget {
  const PlanSelectionScreen({super.key});

  @override
  ConsumerState<PlanSelectionScreen> createState() => _PlanSelectionScreenState();
}

class _PlanSelectionScreenState extends ConsumerState<PlanSelectionScreen> {
  bool _isYearly = true; // Default: annual
  String? _selectedPlanId;

  @override
  Widget build(BuildContext context) {
    final plansAsync = ref.watch(plansProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                Text('Choose Your Plan', style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 20),

                // Billing cycle toggle
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Monthly', style: TextStyle(
                      fontWeight: !_isYearly ? FontWeight.w700 : FontWeight.w400,
                      color: !_isYearly ? AppColors.textPrimary : AppColors.textMuted,
                    )),
                    const SizedBox(width: 12),
                    Switch(
                      value: _isYearly,
                      onChanged: (v) => setState(() => _isYearly = v),
                      activeColor: AppColors.primary,
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Yearly', style: TextStyle(
                          fontWeight: _isYearly ? FontWeight.w700 : FontWeight.w400,
                          color: _isYearly ? AppColors.textPrimary : AppColors.textMuted,
                        )),
                        if (_isYearly)
                          plansAsync.whenOrNull(data: (plans) {
                            final ultra = plans.where((p) => p.slug == 'ultra').firstOrNull;
                            if (ultra != null && ultra.yearlySavings > 0) {
                              return Text('Save ${ultra.yearlySavings.toStringAsFixed(0)}%',
                                  style: TextStyle(fontSize: 11, color: AppColors.success, fontWeight: FontWeight.w600));
                            }
                            return null;
                          }) ?? const SizedBox(),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Plan cards
                Expanded(
                  child: plansAsync.when(
                    data: (plans) => ListView(
                      children: plans.map((plan) => PlanCard(
                        plan: plan,
                        isYearly: _isYearly,
                        isSelected: _selectedPlanId == plan.id,
                        onSelect: () async {
                          setState(() => _selectedPlanId = plan.id);
                          // Subscribe via API
                          final api = ref.read(apiClientProvider);
                          await api.post('/mobile/subscriptions', data: {
                            'plan_id': plan.id,
                            'billing_cycle': _isYearly ? 'yearly' : 'monthly',
                          });
                          if (mounted) {
                            ref.read(authProvider.notifier).completeOnboarding();
                            context.go('/home');
                          }
                        },
                      )).toList(),
                    ),
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text('Error: $e')),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/
git commit -m "feat: add onboarding screens (call, user info, plan selection)"
```

---

### Task 9: Placeholder Screens for Remaining Routes

**Files:**
- Create stubs for all remaining screens to prevent router errors

- [ ] **Step 1: Create stub screens**

Create minimal placeholder widgets for all screens referenced in the router that aren't yet implemented (voice_call, video_call, chat, practice_hub, profile sub-screens, support). Each is a simple `StatelessWidget` with just a `Scaffold(body: Center(child: Text('Screen Name')))`.

```dart
// mobile/lib/screens/learning/voice_call_screen.dart
import 'package:flutter/material.dart';
class VoiceCallScreen extends StatelessWidget {
  final String mode;
  const VoiceCallScreen({super.key, this.mode = 'learning'});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Voice Call - $mode')));
}
```

```dart
// mobile/lib/screens/learning/video_call_screen.dart
import 'package:flutter/material.dart';
class VideoCallScreen extends StatelessWidget {
  final String mode;
  const VideoCallScreen({super.key, this.mode = 'learning'});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Video Call - $mode')));
}
```

```dart
// mobile/lib/screens/learning/chat_screen.dart
import 'package:flutter/material.dart';
class ChatScreen extends StatelessWidget {
  final String mode;
  const ChatScreen({super.key, this.mode = 'learning'});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Chat - $mode')));
}
```

```dart
// mobile/lib/screens/practice/practice_hub_screen.dart
import 'package:flutter/material.dart';
class PracticeHubScreen extends StatelessWidget {
  const PracticeHubScreen({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: Text('Practice Hub'));
}
```

```dart
// mobile/lib/screens/profile/profile_screen.dart
import 'package:flutter/material.dart';
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: Text('Profile'));
}
```

```dart
// mobile/lib/screens/profile/cefr_screen.dart
import 'package:flutter/material.dart';
class CefrScreen extends StatelessWidget {
  const CefrScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(body: Center(child: Text('CEFR Level')));
}
```

```dart
// mobile/lib/screens/profile/history_screen.dart
import 'package:flutter/material.dart';
class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(body: Center(child: Text('History')));
}
```

```dart
// mobile/lib/screens/profile/subscription_screen.dart
import 'package:flutter/material.dart';
class SubscriptionScreen extends StatelessWidget {
  const SubscriptionScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(body: Center(child: Text('Subscription')));
}
```

```dart
// mobile/lib/screens/profile/profile_edit_screen.dart
import 'package:flutter/material.dart';
class ProfileEditScreen extends StatelessWidget {
  const ProfileEditScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(body: Center(child: Text('Edit Profile')));
}
```

```dart
// mobile/lib/screens/profile/transcript_screen.dart
import 'package:flutter/material.dart';
class TranscriptScreen extends StatelessWidget {
  final String sessionId;
  const TranscriptScreen({super.key, required this.sessionId});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Transcript: $sessionId')));
}
```

```dart
// mobile/lib/screens/support/support_screen.dart
import 'package:flutter/material.dart';
class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: Text('Support'));
}
```

- [ ] **Step 2: Verify app compiles**

```bash
cd mobile && flutter analyze
```

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/screens/
git commit -m "feat: add stub screens for all routes to complete navigation shell"
```
