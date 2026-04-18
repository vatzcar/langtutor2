import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/persona_avatar.dart';

/// Profile overview screen showing user data and navigation to sub-pages.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    final plan = ref.watch(currentPlanProvider);
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                const SizedBox(height: 12),

                // Top row: plan name + 4 menu icons
                _buildTopRow(context, planName),

                const SizedBox(height: 24),

                // Persona avatar
                const PersonaAvatar(size: 200, showBorder: true),

                const SizedBox(height: 28),

                // User data card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      _DataRow(label: 'Name', value: user?.name ?? '--'),
                      const Divider(height: 24, color: AppColors.divider),
                      _DataRow(label: 'Email', value: user?.email ?? '--'),
                      const Divider(height: 24, color: AppColors.divider),
                      _DataRow(
                          label: 'Date of Birth',
                          value: user?.dateOfBirth ?? '--'),
                      const Divider(height: 24, color: AppColors.divider),
                      _DataRow(
                          label: 'Country', value: '--'), // placeholder
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Edit button
                Align(
                  alignment: Alignment.centerRight,
                  child: GestureDetector(
                    onTap: () => context.push('/profile/edit'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.navBg,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text(
                        'Edit',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Top row
  // ---------------------------------------------------------------------------

  Widget _buildTopRow(BuildContext context, String planName) {
    return Row(
      children: [
        Text(
          planName,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const Spacer(),
        _MenuIcon(
          icon: Icons.person_rounded,
          isActive: true,
          onTap: () {},
        ),
        const SizedBox(width: 10),
        _MenuIcon(
          icon: Icons.bar_chart_rounded,
          isActive: false,
          onTap: () => context.push('/profile/cefr'),
        ),
        const SizedBox(width: 10),
        _MenuIcon(
          icon: Icons.history_rounded,
          isActive: false,
          onTap: () => context.push('/profile/history'),
        ),
        const SizedBox(width: 10),
        _MenuIcon(
          icon: Icons.credit_card_rounded,
          isActive: false,
          onTap: () => context.push('/profile/subscription'),
        ),
      ],
    );
  }

}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class _MenuIcon extends StatelessWidget {
  const _MenuIcon({
    required this.icon,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.navBg,
          shape: BoxShape.circle,
          border: isActive
              ? Border.all(color: AppColors.navActive, width: 2)
              : null,
        ),
        child: Icon(
          icon,
          color: isActive ? AppColors.navActive : Colors.white70,
          size: 20,
        ),
      ),
    );
  }
}

class _DataRow extends StatelessWidget {
  const _DataRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
          ),
        ),
        const Spacer(),
        Flexible(
          child: Text(
            value,
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.textPrimary,
            ),
            textAlign: TextAlign.end,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
