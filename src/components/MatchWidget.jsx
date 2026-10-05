import React, { useEffect, useState } from 'react';

const MatchWidget = ({ onSelectChannel }) => {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/matches')
      .then((res) => res.json())
      .then((data) => {
        setMatches(data.matches || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching matches:", err);
        setLoading(false);
      });
  }, []);

  if (loading || matches.length === 0) return null;

  return (
    <div style={{ padding: '10px 15px', background: '#121212', borderRadius: '12px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h3 style={{ color: '#fff', fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ height: '10px', width: '10px', backgroundColor: '#e50914', borderRadius: '50%', display: 'inline-block' }}></span>
          مباريات اليوم المباشرة
        </h3>
      </div>

      {/* الشريط الأفقي للمباريات */}
      <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px', scrollbarWidth: 'none' }}>
        {matches.map((match) => {
          const hasStream = !!match.matched_channel;

          return (
            <div
              key={match.id}
              onClick={() => {
                if (hasStream) {
                  onSelectChannel(match.matched_channel.id);
                } else {
                  alert(`القناة الناقلة (${match.tv_channel}) غير متوفرة في قائمة البث حالياً.`);
                }
              }}
              style={{
                minWidth: '220px',
                background: '#1e1e1e',
                border: hasStream ? '1px solid #e50914' : '1px solid #333',
                borderRadius: '10px',
                padding: '10px',
                cursor: hasStream ? 'pointer' : 'default',
                position: 'relative',
                transition: 'transform 0.2s'
              }}
            >
              {/* شارة حالة المباراة */}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#aaa', marginBottom: '8px' }}>
                <span>{match.league}</span>
                <span style={{ color: match.status === 'LIVE' ? '#00ff87' : '#aaa', fontWeight: 'bold' }}>
                  {match.status === 'LIVE' ? 'مباشر ●' : match.time}
                </span>
              </div>

              {/* الفرق والنتيجة */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0' }}>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <img src={match.home_logo} alt={match.home_team} style={{ width: '24px', height: '24px', objectFit: 'contain' }} />
                  <div style={{ fontSize: '12px', color: '#fff', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {match.home_team}
                  </div>
                </div>

                <div style={{ padding: '0 8px', fontSize: '14px', fontWeight: 'bold', color: '#e50914' }}>
                  {match.score}
                </div>

                <div style={{ textAlign: 'center', flex: 1 }}>
                  <img src={match.away_logo} alt={match.away_team} style={{ width: '24px', height: '24px', objectFit: 'contain' }} />
                  <div style={{ fontSize: '12px', color: '#fff', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {match.away_team}
                  </div>
                </div>
              </div>

              {/* القناة الناقلة ورابط الانتقال */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #2a2a2a', fontSize: '11px' }}>
                <span style={{ color: '#888' }}>{match.tv_channel}</span>
                {hasStream ? (
                  <span style={{ color: '#00ff87', fontWeight: 'bold' }}>شاهد الآن ➔</span>
                ) : (
                  <span style={{ color: '#555' }}>غير متاحة</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MatchWidget;
