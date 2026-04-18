import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';

class OnboardingCallScreen extends ConsumerStatefulWidget {
  const OnboardingCallScreen({super.key});

  @override
  ConsumerState<OnboardingCallScreen> createState() =>
      _OnboardingCallScreenState();
}

class _OnboardingCallScreenState extends ConsumerState<OnboardingCallScreen> {
  bool _isConnecting = true;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  Future<void> _connect() async {
    // TODO: connect to coordinator via LiveKit
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      setState(() => _isConnecting = false);
    }
  }

  void _endCall() {
    // TODO: disconnect LiveKit session
    context.go('/onboarding/info');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _isConnecting
                ? _buildConnecting(context)
                : _buildCallActive(context),
          ),
        ),
      ),
    );
  }

  Widget _buildConnecting(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(color: AppColors.primary),
          const SizedBox(height: 24),
          Text(
            'Connecting to coordinator...',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ],
      ),
    );
  }

  Widget _buildCallActive(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 24),

        // Video feed area placeholder
        Expanded(
          flex: 3,
          child: Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppColors.navBg,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Center(
              child: Icon(
                Icons.videocam,
                size: 64,
                color: AppColors.navInactive,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Transcript area
        Expanded(
          flex: 2,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.navBg.withOpacity(0.8),
              borderRadius: BorderRadius.circular(16),
            ),
            child: SingleChildScrollView(
              child: Text(
                '',
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(color: Colors.white70),
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),

        // End call button
        GestureDetector(
          onTap: _endCall,
          child: Container(
            width: 64,
            height: 64,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.error,
            ),
            child: const Icon(
              Icons.stop,
              size: 32,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: 32),
      ],
    );
  }
}
