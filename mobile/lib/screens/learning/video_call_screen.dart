import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';

/// Video-call screen used during learning (or practice) sessions.
class VideoCallScreen extends ConsumerStatefulWidget {
  const VideoCallScreen({super.key, this.mode = 'learning'});

  final String mode;

  @override
  ConsumerState<VideoCallScreen> createState() => _VideoCallScreenState();
}

class _VideoCallScreenState extends ConsumerState<VideoCallScreen> {
  final List<String> _transcript = [];

  @override
  void initState() {
    super.initState();
    _connectToLiveKit();
  }

  Future<void> _connectToLiveKit() async {
    // TODO: connect via LiveKitService with video enabled
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  String _formatTimer(int totalSeconds) {
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _onToggleVoice() {
    final session = ref.read(sessionProvider);
    if (session == null) return;
    ref.read(sessionProvider.notifier).switchType('voice');
    context.pushReplacement(
      '/learning/voice',
      extra: widget.mode,
    );
  }

  Future<void> _onEndCall() async {
    await ref.read(sessionProvider.notifier).endSession();
    if (mounted) context.go('/home');
  }

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final plan = ref.watch(currentPlanProvider);
    final voiceEnabled =
        plan.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgLearning,
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 12),

              // Video feed area
              Expanded(
                flex: 4,
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: AppColors.navBg,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  alignment: Alignment.center,
                  child: const Text(
                    'AI Persona Video',
                    style: TextStyle(color: Colors.white54, fontSize: 18),
                  ),
                ),
              ),

              const SizedBox(height: 8),

              // Transcript area
              Expanded(
                flex: 2,
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.navBg.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _transcript
                          .map(
                            (line) => Padding(
                              padding: const EdgeInsets.only(bottom: 6),
                              child: Text(
                                line,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 8),

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

              const SizedBox(height: 12),

              // Call controls
              _VideoCallControls(
                voiceEnabled: voiceEnabled,
                onToggleVoice: _onToggleVoice,
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
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------

class _VideoCallControls extends StatelessWidget {
  const _VideoCallControls({
    required this.voiceEnabled,
    required this.onToggleVoice,
    required this.onEndCall,
  });

  final bool voiceEnabled;
  final VoidCallback onToggleVoice;
  final VoidCallback onEndCall;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (voiceEnabled)
          GestureDetector(
            onTap: onToggleVoice,
            child: Container(
              width: 52,
              height: 52,
              decoration: const BoxDecoration(
                color: AppColors.primary,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.phone_rounded,
                  color: Colors.white, size: 24),
            ),
          ),
        const SizedBox(width: 24),
        GestureDetector(
          onTap: onEndCall,
          child: Container(
            width: 64,
            height: 64,
            decoration: const BoxDecoration(
              color: AppColors.error,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.call_end_rounded,
                color: Colors.white, size: 28),
          ),
        ),
      ],
    );
  }
}
