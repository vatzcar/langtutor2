# Plan 4: Flutter Learning & Practice Screens

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the voice call, video call, and text chat screens for both learning and practice modes. Integrate LiveKit Flutter SDK for WebRTC calls. Build the practice hub screen.

**Architecture:** Learning screens connect to LiveKit rooms via the Flutter SDK. Session state (timer, usage limits) is managed locally with Riverpod and synced to backend. Call controls switch between voice/video modes. Practice hub reuses the same call/chat components in practice mode.

**Tech Stack:** Flutter, livekit_client, Riverpod, Dio

---

### Task 1: LiveKit Service

**Files:**
- Create: `mobile/lib/services/livekit_service.dart`
- Create: `mobile/lib/providers/session_provider.dart`

- [ ] **Step 1: Create LiveKit service**

```dart
// mobile/lib/services/livekit_service.dart
import 'package:livekit_client/livekit_client.dart';
import '../config/constants.dart';

class LiveKitService {
  Room? _room;
  EventsListener<RoomEvent>? _listener;

  Room? get room => _room;
  bool get isConnected => _room?.connectionState == ConnectionState.connected;

  Future<Room> connect(String token, {bool videoEnabled = true}) async {
    _room = Room();

    _room!.connect(
      AppConstants.livekitUrl,
      token,
      roomOptions: RoomOptions(
        adaptiveStream: true,
        dynacast: true,
        defaultAudioPublishOptions: const AudioPublishOptions(
          audioBitrate: AudioPresets.music,
        ),
        defaultVideoPublishOptions: const VideoPublishOptions(
          videoEncoding: VideoEncoding(maxBitrate: 1700000, maxFramerate: 30),
        ),
      ),
    );

    // Enable microphone (speaker mode)
    await _room!.localParticipant?.setMicrophoneEnabled(true);

    // Set audio output to speaker (hands-free)
    await Hardware.instance.setSpeakerphoneOn(true);

    return _room!;
  }

  Future<void> toggleVideo(bool enabled) async {
    await _room?.localParticipant?.setCameraEnabled(enabled);
  }

  Future<void> disconnect() async {
    await _room?.disconnect();
    _room?.dispose();
    _room = null;
  }

  Stream<RoomEvent>? get events => _listener?.events;

  RemoteParticipant? get remoteParticipant {
    return _room?.remoteParticipants.values.firstOrNull;
  }
}
```

- [ ] **Step 2: Create session provider**

```dart
// mobile/lib/providers/session_provider.dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_provider.dart';

class ActiveSession {
  final String sessionId;
  final String sessionType; // voice_call, video_call, text_chat
  final String sessionMode; // learning, practice, support
  final String? livekitToken;
  final String? roomName;
  final int elapsedSeconds;
  final double remainingMinutes;
  final bool isWarned; // 2-min warning sent

  ActiveSession({
    required this.sessionId,
    required this.sessionType,
    required this.sessionMode,
    this.livekitToken,
    this.roomName,
    this.elapsedSeconds = 0,
    this.remainingMinutes = double.infinity,
    this.isWarned = false,
  });

  ActiveSession copyWith({
    int? elapsedSeconds,
    double? remainingMinutes,
    bool? isWarned,
    String? sessionType,
  }) => ActiveSession(
    sessionId: sessionId,
    sessionType: sessionType ?? this.sessionType,
    sessionMode: sessionMode,
    livekitToken: livekitToken,
    roomName: roomName,
    elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
    remainingMinutes: remainingMinutes ?? this.remainingMinutes,
    isWarned: isWarned ?? this.isWarned,
  );
}

class SessionNotifier extends StateNotifier<ActiveSession?> {
  final Ref _ref;
  Timer? _timer;

  SessionNotifier(this._ref) : super(null);

  Future<void> startSession(String type, String mode, {String? languageId}) async {
    final api = _ref.read(apiClientProvider);
    final resp = await api.post('/mobile/sessions/start', data: {
      'session_type': type,
      'session_mode': mode,
      if (languageId != null) 'language_id': languageId,
    });

    final data = resp.data;
    state = ActiveSession(
      sessionId: data['session_id'],
      sessionType: type,
      sessionMode: mode,
      livekitToken: data['livekit_token'],
      roomName: data['room_name'],
    );

    // Start elapsed timer
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (state != null) {
        final newElapsed = state!.elapsedSeconds + 1;
        final usedMinutes = newElapsed / 60.0;

        // Check remaining time
        final remaining = state!.remainingMinutes - (1 / 60.0);

        state = state!.copyWith(
          elapsedSeconds: newElapsed,
          remainingMinutes: remaining,
          isWarned: remaining <= 2 && remaining > 0,
        );

        // Auto-end at limit
        if (remaining <= 0 && state!.remainingMinutes != double.infinity) {
          endSession();
        }
      }
    });
  }

  void switchType(String newType) {
    if (state != null) {
      state = state!.copyWith(sessionType: newType);
    }
  }

  Future<void> endSession() async {
    _timer?.cancel();
    if (state != null) {
      final api = _ref.read(apiClientProvider);
      await api.post('/mobile/sessions/${state!.sessionId}/end', data: {
        'duration_seconds': state!.elapsedSeconds,
      });
    }
    state = null;
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

final sessionProvider = StateNotifierProvider<SessionNotifier, ActiveSession?>((ref) {
  return SessionNotifier(ref);
});
```

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/services/livekit_service.dart mobile/lib/providers/session_provider.dart
git commit -m "feat: add LiveKit service and session state management"
```

---

### Task 2: Call Controls Widget

**Files:**
- Create: `mobile/lib/widgets/call_controls.dart`

- [ ] **Step 1: Create reusable call controls**

```dart
// mobile/lib/widgets/call_controls.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';

class CallControls extends StatelessWidget {
  final bool isVideoCall;
  final bool videoEnabled;
  final bool voiceEnabled;
  final VoidCallback? onToggleVideo;
  final VoidCallback? onToggleVoice;
  final VoidCallback onEndCall;

  const CallControls({
    super.key,
    required this.isVideoCall,
    this.videoEnabled = true,
    this.voiceEnabled = true,
    this.onToggleVideo,
    this.onToggleVoice,
    required this.onEndCall,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // Video call button
          _ControlButton(
            icon: Icons.videocam,
            isActive: isVideoCall,
            enabled: videoEnabled,
            onTap: onToggleVideo,
          ),

          // End call button (big red circle)
          GestureDetector(
            onTap: onEndCall,
            child: Container(
              width: 72, height: 72,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.error,
                boxShadow: [
                  BoxShadow(color: AppColors.error.withOpacity(0.4), blurRadius: 12, spreadRadius: 2),
                ],
              ),
              child: const Icon(Icons.stop_rounded, color: Colors.white, size: 32),
            ),
          ),

          // Voice call button
          _ControlButton(
            icon: Icons.phone,
            isActive: !isVideoCall,
            enabled: voiceEnabled,
            onTap: onToggleVoice,
          ),
        ],
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  final IconData icon;
  final bool isActive;
  final bool enabled;
  final VoidCallback? onTap;

  const _ControlButton({
    required this.icon,
    required this.isActive,
    required this.enabled,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color bgColor;
    final Color iconColor;

    if (!enabled) {
      bgColor = AppColors.disabledBg;
      iconColor = AppColors.disabled;
    } else if (isActive) {
      bgColor = AppColors.navBg.withOpacity(0.5);
      iconColor = AppColors.disabled;
    } else {
      bgColor = AppColors.navBg;
      iconColor = Colors.white;
    }

    return GestureDetector(
      onTap: enabled && !isActive ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Icon(icon, color: iconColor, size: 28),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/widgets/call_controls.dart
git commit -m "feat: add reusable call controls widget"
```

---

### Task 3: Voice Call Screen

**Files:**
- Modify: `mobile/lib/screens/learning/voice_call_screen.dart`

- [ ] **Step 1: Implement voice call screen**

```dart
// mobile/lib/screens/learning/voice_call_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/persona_avatar.dart';
import '../../widgets/call_controls.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../services/livekit_service.dart';

class VoiceCallScreen extends ConsumerStatefulWidget {
  final String mode;
  const VoiceCallScreen({super.key, this.mode = 'learning'});

  @override
  ConsumerState<VoiceCallScreen> createState() => _VoiceCallScreenState();
}

class _VoiceCallScreenState extends ConsumerState<VoiceCallScreen> {
  final LiveKitService _lkService = LiveKitService();
  String _transcript = '';
  bool _isConnecting = true;

  @override
  void initState() {
    super.initState();
    _connectToRoom();
  }

  Future<void> _connectToRoom() async {
    final session = ref.read(sessionProvider);
    if (session?.livekitToken != null) {
      await _lkService.connect(session!.livekitToken!, videoEnabled: false);
    }
    if (mounted) setState(() => _isConnecting = false);
  }

  @override
  void dispose() {
    _lkService.disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final planAsync = ref.watch(currentPlanProvider);
    final videoEnabled = planAsync.whenOrNull(data: (p) => p?.hasVideoCall) ?? false;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgLearning,
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(),

              // Persona image
              PersonaAvatar(size: 220, showBorder: true),

              const SizedBox(height: 24),

              // Transcript / Subtitle area
              Expanded(
                flex: 3,
                child: Container(
                  width: double.infinity,
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppColors.navBg.withOpacity(0.85),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Text(
                      _transcript.isEmpty ? 'Listening...' : _transcript,
                      style: const TextStyle(color: Colors.white, fontSize: 16, height: 1.5),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Time warning
              if (session?.isWarned == true)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text('Call ending in 2 minutes',
                      style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.w600)),
                ),

              // Timer
              if (session != null)
                Text(
                  _formatTime(session.elapsedSeconds),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),

              const SizedBox(height: 8),

              // Call controls
              CallControls(
                isVideoCall: false,
                videoEnabled: videoEnabled,
                voiceEnabled: false, // Already on voice call
                onToggleVideo: videoEnabled ? () {
                  ref.read(sessionProvider.notifier).switchType('video_call');
                  context.pushReplacement('/learning/video', extra: widget.mode);
                } : null,
                onEndCall: () async {
                  await _lkService.disconnect();
                  await ref.read(sessionProvider.notifier).endSession();
                  if (mounted) context.go('/home');
                },
              ),

              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: widget.mode == 'practice' ? 1 : 0,
        onTap: (_) {},
      ),
    );
  }

  String _formatTime(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/learning/voice_call_screen.dart
git commit -m "feat: implement voice call screen with LiveKit and transcript"
```

---

### Task 4: Video Call Screen

**Files:**
- Modify: `mobile/lib/screens/learning/video_call_screen.dart`

- [ ] **Step 1: Implement video call screen**

```dart
// mobile/lib/screens/learning/video_call_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:livekit_client/livekit_client.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/call_controls.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../services/livekit_service.dart';

class VideoCallScreen extends ConsumerStatefulWidget {
  final String mode;
  const VideoCallScreen({super.key, this.mode = 'learning'});

  @override
  ConsumerState<VideoCallScreen> createState() => _VideoCallScreenState();
}

class _VideoCallScreenState extends ConsumerState<VideoCallScreen> {
  final LiveKitService _lkService = LiveKitService();
  String _transcript = '';
  bool _isConnecting = true;

  @override
  void initState() {
    super.initState();
    _connectToRoom();
  }

  Future<void> _connectToRoom() async {
    final session = ref.read(sessionProvider);
    if (session?.livekitToken != null) {
      await _lkService.connect(session!.livekitToken!, videoEnabled: true);
    }
    if (mounted) setState(() => _isConnecting = false);
  }

  @override
  void dispose() {
    _lkService.disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final planAsync = ref.watch(currentPlanProvider);
    final voiceEnabled = planAsync.whenOrNull(data: (p) => p?.hasVoiceCall) ?? true;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgLearning,
        child: SafeArea(
          child: Column(
            children: [
              // Video feed area (AI persona)
              Expanded(
                flex: 4,
                child: Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(0, 0, 0, 0),
                  decoration: BoxDecoration(
                    color: AppColors.navBg,
                    borderRadius: const BorderRadius.vertical(bottom: Radius.circular(20)),
                  ),
                  child: _isConnecting
                      ? const Center(child: CircularProgressIndicator(color: Colors.white))
                      : _buildVideoView(),
                ),
              ),

              const SizedBox(height: 8),

              // Transcript / Subtitle area
              Expanded(
                flex: 2,
                child: Container(
                  width: double.infinity,
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.navBg.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Text(
                      _transcript.isEmpty ? 'Listening...' : _transcript,
                      style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.4),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 8),

              // Warning
              if (session?.isWarned == true)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('Call ending in 2 minutes',
                      style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.w600, fontSize: 13)),
                ),

              // Timer
              if (session != null)
                Text(_formatTime(session.elapsedSeconds), style: Theme.of(context).textTheme.bodySmall),

              // Call controls
              CallControls(
                isVideoCall: true,
                videoEnabled: false, // Already on video
                voiceEnabled: voiceEnabled,
                onToggleVoice: voiceEnabled ? () {
                  ref.read(sessionProvider.notifier).switchType('voice_call');
                  context.pushReplacement('/learning/voice', extra: widget.mode);
                } : null,
                onEndCall: () async {
                  await _lkService.disconnect();
                  await ref.read(sessionProvider.notifier).endSession();
                  if (mounted) context.go('/home');
                },
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: widget.mode == 'practice' ? 1 : 0,
        onTap: (_) {},
      ),
    );
  }

  Widget _buildVideoView() {
    final remote = _lkService.remoteParticipant;
    if (remote == null) {
      return const Center(child: Text('Waiting for AI tutor...', style: TextStyle(color: Colors.white54)));
    }

    final videoTrack = remote.videoTrackPublications.values
        .where((pub) => pub.track != null)
        .map((pub) => pub.track as VideoTrack)
        .firstOrNull;

    if (videoTrack != null) {
      return ClipRRect(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(20)),
        child: VideoTrackRenderer(videoTrack, fit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover),
      );
    }

    return const Center(child: Text('AI Persona Video', style: TextStyle(color: Colors.white54, fontSize: 18)));
  }

  String _formatTime(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/learning/video_call_screen.dart
git commit -m "feat: implement video call screen with LiveKit video rendering"
```

---

### Task 5: Chat Screen

**Files:**
- Modify: `mobile/lib/screens/learning/chat_screen.dart`
- Create: `mobile/lib/widgets/chat_bubble.dart`
- Create: `mobile/lib/providers/chat_provider.dart`

- [ ] **Step 1: Create chat bubble widget**

```dart
// mobile/lib/widgets/chat_bubble.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';

class ChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  final bool isUnread;

  const ChatBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.isUnread = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (isUnread && !isUser)
            Padding(
              padding: const EdgeInsets.only(right: 4, bottom: 8),
              child: Icon(Icons.priority_high, color: AppColors.accent, size: 16),
            ),
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isUser ? AppColors.primary : AppColors.navBg,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: isUser ? const Radius.circular(16) : const Radius.circular(4),
                  bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(16),
                ),
              ),
              child: Text(
                message,
                style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.4),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Create chat provider**

```dart
// mobile/lib/providers/chat_provider.dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/chat_message.dart';
import 'auth_provider.dart';
import 'session_provider.dart';

class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final bool isLimitReached;
  final bool hasNewUnread;

  ChatState({
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
  }) => ChatState(
    messages: messages ?? this.messages,
    isLoading: isLoading ?? this.isLoading,
    isLimitReached: isLimitReached ?? this.isLimitReached,
    hasNewUnread: hasNewUnread ?? this.hasNewUnread,
  );
}

class ChatNotifier extends StateNotifier<ChatState> {
  final Ref _ref;
  Timer? _pollTimer;

  ChatNotifier(this._ref) : super(ChatState());

  Future<void> loadMessages(String sessionId) async {
    state = state.copyWith(isLoading: true);
    try {
      final api = _ref.read(apiClientProvider);
      final resp = await api.get('/mobile/chat/$sessionId/messages');
      final messages = (resp.data as List).map((e) => ChatMessage.fromJson(e)).toList();
      state = state.copyWith(messages: messages, isLoading: false);
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }

    // Poll for new messages
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _pollMessages(sessionId));
  }

  Future<void> _pollMessages(String sessionId) async {
    try {
      final api = _ref.read(apiClientProvider);
      final resp = await api.get('/mobile/chat/$sessionId/messages');
      final messages = (resp.data as List).map((e) => ChatMessage.fromJson(e)).toList();
      if (messages.length > state.messages.length) {
        final hasNew = messages.skip(state.messages.length).any((m) => m.sender == 'persona');
        state = state.copyWith(messages: messages, hasNewUnread: hasNew);
      }
    } catch (_) {}
  }

  Future<void> sendMessage(String sessionId, String content) async {
    try {
      final api = _ref.read(apiClientProvider);
      await api.post('/mobile/chat/$sessionId/messages', data: {'content': content});
      await _pollMessages(sessionId);
    } catch (_) {}
  }

  void markAsRead() {
    state = state.copyWith(hasNewUnread: false);
  }

  void setLimitReached() {
    state = state.copyWith(isLimitReached: true);
    _pollTimer?.cancel();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(ref);
});
```

- [ ] **Step 3: Implement chat screen**

```dart
// mobile/lib/screens/learning/chat_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/chat_bubble.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../providers/session_provider.dart';
import '../../providers/chat_provider.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String mode;
  const ChatScreen({super.key, this.mode = 'learning'});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  bool _isAtBottom = true;
  bool _isMultiline = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);

    // Load messages after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final session = ref.read(sessionProvider);
      if (session != null) {
        ref.read(chatProvider.notifier).loadMessages(session.sessionId);
      }
    });
  }

  void _onScroll() {
    final atBottom = _scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 50;
    if (atBottom != _isAtBottom) {
      setState(() => _isAtBottom = atBottom);
      if (atBottom) {
        ref.read(chatProvider.notifier).markAsRead();
      }
    }
  }

  void _scrollToBottom() {
    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
    ref.read(chatProvider.notifier).markAsRead();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final chatState = ref.watch(chatProvider);

    // Auto-scroll when at bottom and new messages arrive
    if (_isAtBottom && chatState.messages.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) _scrollToBottom();
      });
    }

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgChat,
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: AppColors.navBg,
                child: Row(
                  children: [
                    // Persona image
                    CircleAvatar(
                      radius: 18,
                      backgroundColor: AppColors.disabledBg,
                      child: Icon(Icons.person, color: AppColors.disabled, size: 20),
                    ),
                    const SizedBox(width: 12),

                    // Language flag + name
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white12,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text('LANG', style: TextStyle(color: Colors.white, fontSize: 11)),
                    ),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text('Language Name', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                    ),

                    // Back button
                    IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.white),
                      onPressed: () {
                        ref.read(sessionProvider.notifier).endSession();
                        context.go('/home');
                      },
                    ),
                  ],
                ),
              ),

              // Messages area
              Expanded(
                child: Stack(
                  children: [
                    ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      itemCount: chatState.messages.length,
                      itemBuilder: (_, index) {
                        final msg = chatState.messages[index];
                        final isUnread = !msg.isRead && msg.sender == 'persona';
                        return ChatBubble(
                          message: msg.content,
                          isUser: msg.sender == 'user',
                          isUnread: isUnread,
                        );
                      },
                    ),

                    // New message indicator
                    if (!_isAtBottom && chatState.hasNewUnread)
                      Positioned(
                        bottom: 8,
                        right: 16,
                        child: GestureDetector(
                          onTap: _scrollToBottom,
                          child: Container(
                            width: 40, height: 40,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppColors.success,
                              boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 6)],
                            ),
                            child: const Icon(Icons.keyboard_arrow_down, color: Colors.white),
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              // Input area
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                color: Colors.white,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        enabled: !chatState.isLimitReached,
                        maxLines: _isMultiline ? 3 : 1,
                        onChanged: (text) {
                          final multiline = text.contains('\n') || text.length > 50;
                          if (multiline != _isMultiline) setState(() => _isMultiline = multiline);
                        },
                        decoration: InputDecoration(
                          hintText: chatState.isLimitReached ? 'Chat limit reached' : 'Type Your Message',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: chatState.isLimitReached ? null : () {
                        final text = _controller.text.trim();
                        if (text.isNotEmpty && session != null) {
                          ref.read(chatProvider.notifier).sendMessage(session.sessionId, text);
                          _controller.clear();
                          setState(() => _isMultiline = false);
                        }
                      },
                      child: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: chatState.isLimitReached ? AppColors.disabledBg : AppColors.primary,
                        ),
                        child: Icon(Icons.send, color: chatState.isLimitReached ? AppColors.disabled : Colors.white, size: 22),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: widget.mode == 'practice' ? 1 : 0,
        onTap: (_) {},
      ),
    );
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add mobile/lib/
git commit -m "feat: implement chat screen with message bubbles, scroll behavior, and limit handling"
```

---

### Task 6: Practice Hub Screen

**Files:**
- Modify: `mobile/lib/screens/practice/practice_hub_screen.dart`

- [ ] **Step 1: Implement practice hub**

```dart
// mobile/lib/screens/practice/practice_hub_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/top_info_bar.dart';
import '../../widgets/persona_avatar.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';
import '../../providers/session_provider.dart';

class PracticeHubScreen extends ConsumerWidget {
  const PracticeHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedLang = ref.watch(selectedLanguageProvider);
    final planAsync = ref.watch(currentPlanProvider);

    return Column(
      children: [
        // Top Info Bar (same as home)
        TopInfoBar(
          cefrLevel: selectedLang?.currentCefrLevel ?? 'A0',
          progressPercent: selectedLang?.cefrProgressPercent ?? 0,
          planName: planAsync.whenOrNull(data: (plan) => plan?.name) ?? 'Free',
        ),

        const SizedBox(height: 16),

        // Title
        Text('PRACTICE HUB',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(letterSpacing: 3)),

        const SizedBox(height: 24),

        // Teacher image
        PersonaAvatar(size: 180, showBorder: true),

        const Spacer(),

        // Call buttons (same layout as home)
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
                  _PracticeButton(
                    icon: Icons.phone,
                    enabled: planAsync.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false,
                    onTap: () async {
                      await ref.read(sessionProvider.notifier).startSession('voice_call', 'practice');
                      if (context.mounted) context.push('/learning/voice', extra: 'practice');
                    },
                  ),
                  Container(width: 1, height: 50, color: Colors.white24),
                  _PracticeButton(
                    icon: Icons.videocam,
                    enabled: planAsync.whenOrNull(data: (p) => p?.hasVideoCall) ?? false,
                    onTap: () async {
                      await ref.read(sessionProvider.notifier).startSession('video_call', 'practice');
                      if (context.mounted) context.push('/learning/video', extra: 'practice');
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        SizedBox(
          width: 200,
          child: ElevatedButton(
            onPressed: () async {
              await ref.read(sessionProvider.notifier).startSession('text_chat', 'practice');
              if (context.mounted) context.push('/learning/chat', extra: 'practice');
            },
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
}

class _PracticeButton extends StatelessWidget {
  final IconData icon;
  final bool enabled;
  final VoidCallback? onTap;

  const _PracticeButton({required this.icon, required this.enabled, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        child: Icon(icon, size: 36, color: enabled ? Colors.white : AppColors.disabled),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/practice/
git commit -m "feat: implement practice hub screen with call/chat buttons"
```
