import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/persona_avatar.dart';

/// Voice-call screen used during learning (or practice) sessions.
class VoiceCallScreen extends ConsumerStatefulWidget {
  const VoiceCallScreen({super.key, this.mode = 'learning'});

  final String mode;

  @override
  ConsumerState<VoiceCallScreen> createState() => _VoiceCallScreenState();
}

class _VoiceCallScreenState extends ConsumerState<VoiceCallScreen> {
  final List<String> _transcript = [];

  @override
  void initState() {
    super.initState();
    _connectToLiveKit();
  }

  /// Stubbed LiveKit connection -- will be wired up when backend is ready.
  Future<void> _connectToLiveKit() async {
    // TODO: connect via LiveKitService using session.livekitToken
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  String _formatTimer(int totalSeconds) {
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _onToggleVideo() {
    final session = ref.read(sessionProvider);
    if (session == null) return;
    ref.read(sessionProvider.notifier).switchType('video');
    context.pushReplacement(
      '/learning/video',
      extra: widget.mode,
    );
  }

  Future<void> _onEndCall() async {
    await ref.read(sessionProvider.notifier).endSession();
    if (mounted) context.go('/home');
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final plan = ref.watch(currentPlanProvider);
    final videoEnabled =
        plan.whenOrNull(data: (p) => p?.hasVideoCall) ?? false;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgLearning,
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 24),

              // Persona avatar
              const PersonaAvatar(size: 220, showBorder: true),

              const SizedBox(height: 20),

              // Transcript area
              Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.navBg.withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _transcript
                          .map(
                            (line) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Text(
                                line,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 12),

              // Time warning
              if (session?.isWarned == true)
                const Padding(
                  padding: EdgeInsets.only(bottom: 4),
                  child: Text(
                    'Call ending in 2 minutes',
                    style: TextStyle(
                      color: AppColors.accent,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),

              // Timer
              Text(
                _formatTimer(session?.elapsedSeconds ?? 0),
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),

              const SizedBox(height: 16),

              // Call controls
              _CallControls(
                isVideoCall: false,
                videoEnabled: videoEnabled,
                voiceEnabled: false, // already on voice
                onToggleVideo: _onToggleVideo,
                onToggleVoice: null,
                onEndCall: _onEndCall,
              ),

              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: 0,
        onTap: (i) => _navigateTab(context, i),
      ),
    );
  }

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }
}

// ---------------------------------------------------------------------------
// Shared call controls row
// ---------------------------------------------------------------------------

class _CallControls extends StatelessWidget {
  const _CallControls({
    required this.isVideoCall,
    required this.videoEnabled,
    required this.voiceEnabled,
    this.onToggleVideo,
    this.onToggleVoice,
    required this.onEndCall,
  });

  final bool isVideoCall;
  final bool videoEnabled;
  final bool voiceEnabled;
  final VoidCallback? onToggleVideo;
  final VoidCallback? onToggleVoice;
  final VoidCallback onEndCall;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Toggle to video
        if (!isVideoCall && videoEnabled)
          _ControlButton(
            icon: Icons.videocam_rounded,
            color: AppColors.primary,
            onTap: onToggleVideo,
          ),

        // Toggle to voice
        if (isVideoCall && voiceEnabled)
          _ControlButton(
            icon: Icons.phone_rounded,
            color: AppColors.primary,
            onTap: onToggleVoice,
          ),

        const SizedBox(width: 24),

        // End call
        _ControlButton(
          icon: Icons.call_end_rounded,
          color: AppColors.error,
          onTap: onEndCall,
          size: 64,
        ),
      ],
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.color,
    this.onTap,
    this.size = 52,
  });

  final IconData icon;
  final Color color;
  final VoidCallback? onTap;
  final double size;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
        ),
        child: Icon(icon, color: Colors.white, size: size * 0.45),
      ),
    );
  }
}
