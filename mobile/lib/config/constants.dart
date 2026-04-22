/// App-wide constants for LangTutor.
class AppConstants {
  AppConstants._();

  // ---------- API ----------
  /// Base URL for the backend API.
  ///
  /// For a **physical device on USB**, use `localhost` + run once after each
  /// device reconnect:
  ///   adb reverse tcp:8001 tcp:8001
  ///   adb reverse tcp:7880 tcp:7880
  ///
  /// For the **Android emulator**, change to `http://10.0.2.2:8001/api/v1`.
  /// For a device on the **same Wi-Fi**, use your PC's LAN IP, e.g.
  /// `http://192.168.1.42:8001/api/v1`.
  static const String apiBaseUrl = 'http://38.224.253.71:8001/api/v1';

  // ---------- LiveKit ----------
  /// WebSocket URL for the LiveKit server. See apiBaseUrl comment for the
  /// physical-device / emulator / LAN variants.
  static const String liveKitUrl = 'ws://38.224.253.71:7880';

  // ---------- Auth ----------
  /// Access-token lifetime in hours.
  static const int tokenExpiryHours = 24;

  /// Duration object for convenience.
  static const Duration tokenExpiry = Duration(hours: tokenExpiryHours);

  // ---------- Chat ----------
  /// Delay before the chat view auto-scrolls to the latest message.
  static const Duration chatAutoScrollDelay = Duration(seconds: 5);

  // ---------- Google Sign-In ----------
  /// The **Web** OAuth 2.0 client ID from the same Google Cloud project that
  /// hosts your Android OAuth client. This is required on Android to receive
  /// an `idToken` from `google_sign_in` (without it, `idToken` is null).
  ///
  /// Get it from: Google Cloud Console → Credentials → create OAuth client
  /// with Application type = Web. Example format:
  ///   1234567890-abcdefghij.apps.googleusercontent.com
  ///
  /// The backend must also trust this same ID (set
  /// LANGTUTOR_GOOGLE_CLIENT_ID to the same value), because ID tokens are
  /// issued against the `aud` = this Web client ID.
  static const String googleServerClientId =
      '597944896701-obmhoieoh93v7dd6donjr0v5qfgpph43.apps.googleusercontent.com';
}
