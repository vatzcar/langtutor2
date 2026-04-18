import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/practice/practice_hub_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/support/support_screen.dart';
import '../screens/onboarding/onboarding_call_screen.dart';
import '../screens/onboarding/user_info_screen.dart';
import '../screens/onboarding/plan_selection_screen.dart';
import '../screens/learning/voice_call_screen.dart';
import '../screens/learning/video_call_screen.dart';
import '../screens/learning/chat_screen.dart';
import '../screens/profile/cefr_screen.dart';
import '../screens/profile/history_screen.dart';
import '../screens/profile/subscription_screen.dart';
import '../screens/profile/profile_edit_screen.dart';
import '../screens/profile/transcript_screen.dart';
import '../widgets/bottom_nav_bar.dart';
import '../widgets/bubble_background.dart';
import 'theme.dart';

// ---------------------------------------------------------------------------
// Navigator keys
// ---------------------------------------------------------------------------

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

// ---------------------------------------------------------------------------
// Router provider
// ---------------------------------------------------------------------------

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    redirect: (context, state) {
      final status = authState.status;
      final location = state.matchedLocation;

      // Still loading – don't redirect yet.
      if (status == AuthStatus.initial) return null;

      final isOnLogin = location == '/login';
      final isOnOnboarding = location.startsWith('/onboarding');

      // Not authenticated -> force login.
      if (status == AuthStatus.unauthenticated && !isOnLogin) {
        return '/login';
      }

      // Authenticated user sitting on login -> send home.
      if (status == AuthStatus.authenticated && isOnLogin) {
        return '/home';
      }

      // Onboarding user must stay on onboarding flow.
      if (status == AuthStatus.onboarding && !isOnOnboarding) {
        return '/onboarding';
      }

      return null;
    },
    routes: [
      // ---- Auth ----
      GoRoute(
        path: '/login',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const LoginScreen(),
      ),

      // ---- Onboarding ----
      GoRoute(
        path: '/onboarding',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const OnboardingCallScreen(),
        routes: [
          GoRoute(
            path: 'info',
            parentNavigatorKey: _rootNavigatorKey,
            builder: (context, state) => const UserInfoScreen(),
          ),
          GoRoute(
            path: 'plan',
            parentNavigatorKey: _rootNavigatorKey,
            builder: (context, state) => const PlanSelectionScreen(),
          ),
        ],
      ),

      // ---- Main shell (bottom nav) ----
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) =>
            _AppShell(state: state, child: child),
        routes: [
          GoRoute(
            path: '/home',
            parentNavigatorKey: _shellNavigatorKey,
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            path: '/practice',
            parentNavigatorKey: _shellNavigatorKey,
            builder: (context, state) => const PracticeHubScreen(),
          ),
          GoRoute(
            path: '/profile',
            parentNavigatorKey: _shellNavigatorKey,
            builder: (context, state) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/support',
            parentNavigatorKey: _shellNavigatorKey,
            builder: (context, state) => const SupportScreen(),
          ),
        ],
      ),

      // ---- Full-screen routes (no bottom nav) ----
      GoRoute(
        path: '/learning/voice',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            VoiceCallScreen(mode: state.extra as String? ?? 'learning'),
      ),
      GoRoute(
        path: '/learning/video',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            VideoCallScreen(mode: state.extra as String? ?? 'learning'),
      ),
      GoRoute(
        path: '/learning/chat',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            ChatScreen(mode: state.extra as String? ?? 'learning'),
      ),
      GoRoute(
        path: '/profile/cefr',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const CefrScreen(),
      ),
      GoRoute(
        path: '/profile/history',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const HistoryScreen(),
      ),
      GoRoute(
        path: '/profile/subscription',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SubscriptionScreen(),
      ),
      GoRoute(
        path: '/profile/edit',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ProfileEditScreen(),
      ),
      GoRoute(
        path: '/profile/transcript/:sessionId',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => TranscriptScreen(
          sessionId: state.pathParameters['sessionId']!,
        ),
      ),
    ],
  );
});

// ---------------------------------------------------------------------------
// App shell – wraps tab screens with BubbleBackground + bottom nav
// ---------------------------------------------------------------------------

class _AppShell extends StatefulWidget {
  const _AppShell({required this.state, required this.child});

  final GoRouterState state;
  final Widget child;

  @override
  State<_AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<_AppShell> {
  int _currentIndex = 0;

  static const _routes = ['/home', '/practice', '/profile', '/support'];

  static const _bgColors = [
    AppColors.bgHome,
    AppColors.bgPractice,
    AppColors.bgProfile,
    AppColors.bgSupport,
  ];

  @override
  void didUpdateWidget(covariant _AppShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncIndex();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncIndex();
  }

  void _syncIndex() {
    final location = widget.state.matchedLocation;
    final idx = _routes.indexWhere((r) => location.startsWith(r));
    if (idx != -1 && idx != _currentIndex) {
      setState(() => _currentIndex = idx);
    }
  }

  void _onTap(int index) {
    if (index != _currentIndex) {
      setState(() => _currentIndex = index);
      context.go(_routes[index]);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BubbleBackground(
        backgroundColor: _bgColors[_currentIndex],
        child: SafeArea(child: widget.child),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: _currentIndex,
        onTap: _onTap,
      ),
    );
  }
}
