import React, { useEffect, useState, useCallback } from 'react';
import './App.css';
import useWebSocket from 'react-use-websocket';

const CONNECTION_STATUS_CONNECTING = 0;
const CONNECTION_STATUS_OPEN = 1;
const CONNECTION_STATUS_CLOSING = 2;
const CONNECTION_STATUS_CLOSED = 3;

const WebSocketDemo = () => {
  const [socketUrl, setSocketUrl] = useState('ws://127.0.0.1:8080/ws'); //Public API that will echo messages sent to it back to the client
  const [messageHistory, setMessageHistory] = useState([]);
  const [sendMessage, lastMessage, readyState, getWebSocket] = useWebSocket(socketUrl);

  // const handleClickChangeSocketUrl = useCallback(() => setSocketUrl('wss://demos.kaazing.com/echo'), []);
  const handleClickSendMessage = useCallback(() => sendMessage('Hello'), [sendMessage]);

  useEffect(() => {
    if (lastMessage !== null) {

      //getWebSocket returns the WebSocket wrapped in a Proxy. This is to restrict actions like mutating a shared websocket, overwriting handlers, etc
      const currentWebsocketUrl = getWebSocket().url;
      console.log('received a message from ', currentWebsocketUrl);

      setMessageHistory(prev => prev.concat(lastMessage));
    }
  }, [lastMessage, getWebSocket]);

  const connectionStatus = {
    [CONNECTION_STATUS_CONNECTING]: 'Connecting',
    [CONNECTION_STATUS_OPEN]: 'Open',
    [CONNECTION_STATUS_CLOSING]: 'Closing',
    [CONNECTION_STATUS_CLOSED]: 'Closed',
  }[readyState];

  return (
    <div>
      {/* <br /><button onClick={handleClickChangeSocketUrl}>Click Me to change Socket Url</button> */}
      <br /><button onClick={handleClickSendMessage} disabled={readyState !== CONNECTION_STATUS_OPEN}>Click Me to send 'Hello'</button>
      <br /><span>The WebSocket is currently {connectionStatus}</span>
      <br /><span>Last message: {lastMessage ? lastMessage.data : "null"}</span>
      <br /><ul>
        {messageHistory.map((message, idx) => <span key={idx}>{message.data}</span>)}
      </ul>
    </div>
  );
};

function App() {
  return (
    <React.Fragment>
      <h1>sdf</h1>
      <WebSocketDemo />
    </React.Fragment>
  );
}

export default App;
