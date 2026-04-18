import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';

// ---------------------------------------------------------------------------
// Service providers
// ---------------------------------------------------------------------------

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref.watch(apiClientProvider));
});

// ---------------------------------------------------------------------------
// Auth state
// ---------------------------------------------------------------------------

enum AuthStatus { initial, authenticated, unauthenticated, onboarding }

class AuthState {
  final AuthStatus status;
  final User? user;
  final bool isNewUser;
  final String? error;

  const AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.isNewUser = false,
    this.error,
  });

  AuthState copyWith({
    AuthStatus? status,
    User? user,
    bool? isNewUser,
    String? error,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      isNewUser: isNewUser ?? this.isNewUser,
      error: error,
    );
  }
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final ApiClient _apiClient;

  AuthNotifier(this._authService, this._apiClient) : super(const AuthState()) {
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    try {
      final loggedIn = await _authService.isLoggedIn();
      if (!loggedIn) {
        state = state.copyWith(status: AuthStatus.unauthenticated);
        return;
      }

      final response = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(response.data as Map<String, dynamic>);
      state = state.copyWith(status: AuthStatus.authenticated, user: user);
    } catch (_) {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> signInWithGoogle() async {
    try {
      final data = await _authService.signInWithGoogle();
      final isNew = data['is_new_user'] as bool? ?? false;

      final response = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(response.data as Map<String, dynamic>);

      state = state.copyWith(
        status: isNew ? AuthStatus.onboarding : AuthStatus.authenticated,
        user: user,
        isNewUser: isNew,
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: e.toString(),
      );
    }
  }

  Future<void> signInWithApple() async {
    try {
      final data = await _authService.signInWithApple();
      final isNew = data['is_new_user'] as bool? ?? false;

      final response = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(response.data as Map<String, dynamic>);

      state = state.copyWith(
        status: isNew ? AuthStatus.onboarding : AuthStatus.authenticated,
        user: user,
        isNewUser: isNew,
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: e.toString(),
      );
    }
  }

  void completeOnboarding() {
    state = state.copyWith(
      status: AuthStatus.authenticated,
      isNewUser: false,
    );
  }

  Future<void> signOut() async {
    await _authService.signOut();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  Future<void> refreshUser() async {
    try {
      final response = await _apiClient.get('/mobile/users/me');
      final user = User.fromJson(response.data as Map<String, dynamic>);
      state = state.copyWith(user: user);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    ref.watch(authServiceProvider),
    ref.watch(apiClientProvider),
  );
});
