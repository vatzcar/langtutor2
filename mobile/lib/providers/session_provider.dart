import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_client.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Helper typedef so the notifier doesn't hold a direct Ref.
// ---------------------------------------------------------------------------

typedef ApiClientGetter = ApiClient Function();

// ---------------------------------------------------------------------------
// Active session model
// ---------------------------------------------------------------------------

class ActiveSession {
  final String sessionId;
  final String sessionType;
  final String sessionMode;
  final String? livekitToken;
  final String? roomName;
  final int elapsedSeconds;
  final int remainingMinutes;
  final bool isWarned;

  const ActiveSession({
    required this.sessionId,
    required this.sessionType,
    required this.sessionMode,
    this.livekitToken,
    this.roomName,
    this.elapsedSeconds = 0,
    this.remainingMinutes = 0,
    this.isWarned = false,
  });

  ActiveSession copyWith({
    String? sessionId,
    String? sessionType,
    String? sessionMode,
    String? livekitToken,
    String? roomName,
    int? elapsedSeconds,
    int? remainingMinutes,
    bool? isWarned,
  }) {
    return ActiveSession(
      sessionId: sessionId ?? this.sessionId,
      sessionType: sessionType ?? this.sessionType,
      sessionMode: sessionMode ?? this.sessionMode,
      livekitToken: livekitToken ?? this.livekitToken,
      roomName: roomName ?? this.roomName,
      elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
      remainingMinutes: remainingMinutes ?? this.remainingMinutes,
      isWarned: isWarned ?? this.isWarned,
    );
  }
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class SessionNotifier extends StateNotifier<ActiveSession?> {
  final ApiClientGetter _getApiClient;
  Timer? _timer;

  SessionNotifier(this._getApiClient) : super(null);

  /// Start a new session of the given [type] and [mode].
  Future<void> startSession({
    required String type,
    required String mode,
    String? languageId,
  }) async {
    final apiClient = _getApiClient();
    final response = await apiClient.post(
      '/mobile/sessions/start',
      data: {
        'session_type': type,
        'session_mode': mode,
        if (languageId != null) 'language_id': languageId,
      },
    );

    final data = response.data as Map<String, dynamic>;

    state = ActiveSession(
      sessionId: data['session_id'] as String,
      sessionType: type,
      sessionMode: mode,
      livekitToken: data['livekit_token'] as String?,
      roomName: data['room_name'] as String?,
      remainingMinutes: (data['remaining_minutes'] as num?)?.toInt() ?? 0,
    );

    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      final current = state;
      if (current == null) return;

      final newElapsed = current.elapsedSeconds + 1;
      final newRemaining =
          current.remainingMinutes - (newElapsed ~/ 60);

      state = current.copyWith(
        elapsedSeconds: newElapsed,
        remainingMinutes: newRemaining < 0 ? 0 : newRemaining,
      );
    });
  }

  /// Switch the session type mid-session.
  void switchType(String newType) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(sessionType: newType);
  }

  /// End the current session.
  Future<void> endSession() async {
    final current = state;
    if (current == null) return;

    _timer?.cancel();
    _timer = null;

    final apiClient = _getApiClient();
    await apiClient.post('/sessions/${current.sessionId}/end');

    state = null;
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final sessionProvider =
    StateNotifierProvider<SessionNotifier, ActiveSession?>((ref) {
  return SessionNotifier(() => ref.read(apiClientProvider));
});
