import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/constants.dart';
import 'api_client.dart';

class AuthService {
  final ApiClient _apiClient;
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    // Passing the Web client ID is what makes google_sign_in on Android
    // return an `idToken`. Without it, `idToken` is always null and the
    // backend has no way to verify who the user is.
    serverClientId: AppConstants.googleServerClientId,
    scopes: const ['email', 'profile', 'openid'],
  );

  AuthService(this._apiClient);

  /// Sign in via Google and authenticate with the backend.
  Future<Map<String, dynamic>> signInWithGoogle() async {
    final account = await _googleSignIn.signIn();
    if (account == null) {
      throw Exception('Google sign-in was cancelled');
    }

    final authentication = await account.authentication;
    final idToken = authentication.idToken;
    if (idToken == null) {
      throw Exception('Failed to obtain Google ID token');
    }

    return _authenticateWithBackend('google', idToken);
  }

  /// Sign in via Apple and authenticate with the backend.
  Future<Map<String, dynamic>> signInWithApple() async {
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );

    final identityToken = credential.identityToken;
    if (identityToken == null) {
      throw Exception('Failed to obtain Apple identity token');
    }

    return _authenticateWithBackend('apple', identityToken);
  }

  /// Exchange the provider token for a backend access token.
  Future<Map<String, dynamic>> _authenticateWithBackend(
    String provider,
    String idToken,
  ) async {
    final response = await _apiClient.post(
      '/auth/social-login',
      data: {
        'provider': provider,
        'id_token': idToken,
      },
    );

    final data = response.data as Map<String, dynamic>;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', data['access_token'] as String);
    await prefs.setString('user_id', data['user_id'] as String);

    return data;
  }

  /// Sign out – clear stored credentials and sign out of Google.
  Future<void> signOut() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    await _googleSignIn.signOut();
  }

  /// Whether the user currently has a stored access token.
  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey('access_token');
  }
}
