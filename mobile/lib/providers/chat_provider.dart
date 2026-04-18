import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_client.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Chat message model
// ---------------------------------------------------------------------------

class ChatMessage {
  final String id;
  final String sessionId;
  final String role;
  final String content;
  final DateTime createdAt;

  const ChatMessage({
    required this.id,
    required this.sessionId,
    required this.role,
    required this.content,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      sessionId: json['session_id'] as String,
      role: json['role'] as String,
      content: json['content'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

// ---------------------------------------------------------------------------
// Chat state
// ---------------------------------------------------------------------------

class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final bool isLimitReached;
  final bool hasNewUnread;

  const ChatState({
    this.messages = const [],
    this.isLoading = false,
    this.isLimitReached = false,
    this.hasNewUnread = false,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    bool? isLimitReached,
    bool? hasNewUnread,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      isLimitReached: isLimitReached ?? this.isLimitReached,
      hasNewUnread: hasNewUnread ?? this.hasNewUnread,
    );
  }
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class ChatNotifier extends StateNotifier<ChatState> {
  final ApiClient _apiClient;
  Timer? _pollTimer;

  ChatNotifier(this._apiClient) : super(const ChatState());

  /// Load existing messages for [sessionId] and start polling for new ones.
  Future<void> loadMessages(String sessionId) async {
    state = state.copyWith(isLoading: true);

    try {
      final response =
          await _apiClient.get('/mobile/sessions/$sessionId/messages');
      final items = response.data as List<dynamic>;
      final messages = items
          .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
          .toList();

      state = state.copyWith(messages: messages, isLoading: false);
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }

    // Start polling every 2 seconds.
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final response =
            await _apiClient.get('/mobile/sessions/$sessionId/messages');
        final items = response.data as List<dynamic>;
        final messages = items
            .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
            .toList();

        final hadNew = messages.length > state.messages.length;
        state = state.copyWith(
          messages: messages,
          hasNewUnread: hadNew ? true : state.hasNewUnread,
        );
      } catch (_) {
        // Silently ignore poll errors.
      }
    });
  }

  /// Send a chat message to the given [sessionId].
  Future<void> sendMessage(String sessionId, String content) async {
    try {
      final response = await _apiClient.post(
        '/mobile/sessions/$sessionId/messages',
        data: {'content': content},
      );
      final message =
          ChatMessage.fromJson(response.data as Map<String, dynamic>);
      state = state.copyWith(
        messages: [...state.messages, message],
      );
    } catch (_) {
      // Caller can inspect state for errors if needed.
    }
  }

  /// Mark all messages as read.
  void markAsRead() {
    state = state.copyWith(hasNewUnread: false);
  }

  /// Signal that the usage limit has been reached.
  void setLimitReached() {
    state = state.copyWith(isLimitReached: true);
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(ref.watch(apiClientProvider));
});
