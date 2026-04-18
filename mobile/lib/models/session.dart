class LearningSession {
  final String id;
  final String sessionType;
  final String sessionMode;
  final int durationSeconds;
  final String? cefrLevelAtTime;
  final String startedAt;
  final String? endedAt;

  const LearningSession({
    required this.id,
    required this.sessionType,
    required this.sessionMode,
    required this.durationSeconds,
    this.cefrLevelAtTime,
    required this.startedAt,
    this.endedAt,
  });

  factory LearningSession.fromJson(Map<String, dynamic> json) {
    return LearningSession(
      id: json['id'] as String,
      sessionType: json['session_type'] as String,
      sessionMode: json['session_mode'] as String,
      durationSeconds: json['duration_seconds'] as int,
      cefrLevelAtTime: json['cefr_level_at_time'] as String?,
      startedAt: json['started_at'] as String,
      endedAt: json['ended_at'] as String?,
    );
  }
}
