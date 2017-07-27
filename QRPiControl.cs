using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RestSharp;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

namespace TelegramBotGUI
{
    /// <summary>
    /// Мой переопределённый WebClient с возможностью изменения таймаута
    /// </summary>
    class MyTimeoutWebClient : WebClient
    {
        private int _timeout;

        public MyTimeoutWebClient(int timeoutInSeconds) : base()
        {
            _timeout = timeoutInSeconds * 1000;
        }

        protected override WebRequest GetWebRequest(Uri uri)
        {
            WebRequest w = base.GetWebRequest(uri);
            w.Timeout = _timeout;
            return w;
        }
    }

    /// <summary>
    /// Данные о процессоре
    /// </summary>
    public struct CpuInfo
    {
        public float Temperature;
        public float Usage;

        public CpuInfo(float temp, float usg)
        {
            Usage = usg;
            Temperature = temp;
        }
    }

    /// <summary>
    /// Данные о памяти
    /// </summary>
    public struct MemoryInfo
    {
        public long Total;
        public float TotalKb
        {
            get
            {
                return Total / 1024f;
            }
        }
        public float TotalMb
        {
            get
            {
                return Total / 1024f / 1024f;
            }
        }
        public float UsedPercent;
        public long Used
        {
            get
            {
                return (long)(Total * UsedPercent) / 100;
            }
        }
        public float UsedKb
        {
            get
            {
                return Used / 1024f;
            }
        }
        public float UsedMb
        {
            get
            {
                return Used / 1024f / 1024f;
            }
        }
        public long Free
        {
            get
            {
                return Total - Used;
            }
        }
        public float FreeKb
        {
            get
            {
                return Free / 1024f;
            }
        }
        public float FreeMb
        {
            get
            {
                return Free / 1024f / 1024f;
            }
        }

        public MemoryInfo(long totalmemory, float usedpercent)
        {
            Total = totalmemory;
            UsedPercent = usedpercent;
        }
    }

    /// <summary>
    /// Данные с датчика DHT
    /// </summary>
    public struct DHTInfo
    {
        public float Temp;
        public float Hum;
    }

    /// <summary>
    /// Данные с Raspberry Pi
    /// </summary>
    public struct PiInfo
    {
        private static PiInfo _NotFound = new PiInfo() { PiFound = false };
        public bool PiFound { get; private set; }
        public CpuInfo Cpu { get; set; }
        public MemoryInfo Memory { get; set; }
        public DHTInfo Dht { get; set; }
        public Dictionary<int, GPIOValue> Gpio { get; }

        public static PiInfo NotFound
        {
            get
            {
                return _NotFound;
            }
        }

        public PiInfo(float cputemp, float cpuusg, long totalMemory, float usedMemoryPercent, DHTInfo dht, Dictionary<int, GPIOValue> gpios = null)
        {
            PiFound = true;

            Gpio = gpios ?? new Dictionary<int, GPIOValue>();
            Cpu = new CpuInfo(cputemp, cpuusg);
            Memory = new MemoryInfo(totalMemory, usedMemoryPercent);
            Dht = dht;

        }
    }

    /// <summary>
    /// Данные о боте
    /// </summary>
    public class BotInfo
    {
        public int id;
        public string name;
        public string path;
        public bool running;
        public int pid;
        public bool autorun;
    }

    /// <summary>
    /// Событие о возникновении проблем с Raspberry Pi (Перегрев, Высокая нагрузка)
    /// </summary>
    public class PiProblemEventArgs : EventArgs
    {
        public float Temperature { get; private set; }
        public float FreeMemory { get; private set; } // in %
        public float CpuUsage { get; private set; } // in %

        public PiProblemEventArgs(CpuInfo cpu, MemoryInfo mem)
        {
            CpuUsage = cpu.Usage;
            FreeMemory = 100 - mem.UsedPercent;
            Temperature = cpu.Temperature;
        }
    }

    /// <summary>
    /// API-статус
    /// </summary>
    internal enum ApiStatus
    {
        Success = 0,
        Failed = -1,
        JsonUnexpected = -2,
        JsonParsingError = -3,
        PiNotFound = -4
    }

    /// <summary>
    /// Внутренний ответ от сервера
    /// </summary>
    internal class ApiResponce
    {
        public ApiStatus State;
        public IRestResponse Responce;
        public JObject Json;

        public ApiResponce(IRestResponse responce, JObject json)
        {
            Responce = responce;
            State = ApiStatus.Success;
            Json = json;
        }

        public ApiResponce(ApiStatus status)
        {
            State = status;
        }
    }

    /// <summary>
    /// Результат выполнения обращения к API
    /// </summary>
    /// <typeparam name="T"></typeparam>
    internal class ApiResult<T>
    {
        public ApiStatus Status { get; }
        public T Result { get; }

        public ApiResult(ApiStatus status)
        {
            if (typeof(T) == typeof(bool))
            {
                var res = status == ApiStatus.Success ? true : false;
                Result = (T)Convert.ChangeType(res, typeof(T));
            }
            Status = status;
        }

        public ApiResult(T data)
        {
            Result = data;
            Status = ApiStatus.Success;
        }

        public ApiResult(T data, ApiStatus status)
        {
            Result = data;
            Status = status;
        }

        public static implicit operator ApiResult<T>(T value)
        {
            return new ApiResult<T>(value);
        }

        public static implicit operator ApiResult<T>(ApiStatus value)
        {
            return new ApiResult<T>(value);
        }

        public static bool operator ==(ApiResult<T> t, ApiStatus value)
        {
            return t.Status == value;
        }

        public static bool operator !=(ApiResult<T> t, ApiStatus value)
        {
            return t.Status != value;
        }

        public override bool Equals(object obj)
        {
            return base.Equals(obj);
        }

        public override int GetHashCode()
        {
            return base.GetHashCode();
        }
    }

    public enum GPIODirection
    {
        Unknown = -1,
        NA = -1,
        DontChange = -1,
        In = 1,
        Out = 0
    }

    public enum GPIOValue
    {
        Unknown = -1,
        NA = -1,
        DontChange = -1,
        High = 1,
        Low = 0
    }

    public enum GPIOResistor
    {
        Unknown = -1,
        NA = -1,
        DontChange = -1,
        Disabled = 20,
        PullUp = 21,
        PullDown = 21
    }

    // Rev 2
    public enum GPIONames
    {
        P0 = 17,
        P1 = 18,
        P2 = 27,
        P3 = 22,
        P4 = 23,
        P5 = 24,
        P6 = 25,
        P7 = 4,
        CE1 = 8,
        CE0 = 7,
        SCLK = 11,
        MISO = 9,
        MOSI = 10,
        RXD = 15,
        TXD = 14,
        SCL = 3,
        SDA = 2,
    }
    
    /// <summary>
    /// Данные о пине
    /// </summary>
    public class PinInfo
    {
        public GPIODirection Direction { get; set; }
        public GPIOResistor Resistor { get; set; }
        public GPIOValue Value { get; set; }
    }

    /// <summary>
    /// Управление Raspberry Pi
    /// </summary>
    static class QRPiControl
    {
        private static RestClient RestClient;
        private static string piwebserver = "http://192.168.1.101:5000/";
        private static IPAddress piIP = IPAddress.Parse("192.168.1.101");
        private static int Port = 5000;
        private static WebClient wc = new MyTimeoutWebClient(2);

        /// <summary>
        /// Дата и время последнего дисконнекта
        /// </summary>
        public static DateTime LastDisconnect { get; private set; }
        /// <summary>
        /// Дата и время последнего подключения
        /// </summary>
        public static DateTime LastConnect { get; private set; }

        /// <summary>
        /// Raspberry Pi включена, сервер запущен и доступен по адресу 192.168.1.101:5000
        /// </summary>
        public static bool PiFound { get; private set; }

        public static event EventHandler<EventArgs> Updating;
        public static event EventHandler<EventArgs> Updated;
        public static event EventHandler<EventArgs> Online;
        public static event EventHandler<EventArgs> Offline;
        public static event EventHandler<EventArgs> Finding;

        static QRPiControl()
        {
            Online += (s, e) => { LastConnect = DateTime.UtcNow; };
            Offline += (s, e) => { LastDisconnect = DateTime.UtcNow; };

            RestClient = new RestClient(piwebserver + "api/");
            RestClient.FollowRedirects = false;
        }

        private static bool PingHost(string HostURI, int PortNumber)
        {
            try
            {
                using (TcpClient client = new TcpClient(HostURI, PortNumber))
                {
                    client.Close();
                    return true;
                }
            }
            catch (Exception ex)
            {
                return false;
            }
        }
        public static bool CheckForPi()
        {
            Finding?.Invoke(null, EventArgs.Empty);
            var found =  PingHost(piIP.ToString(), Port);

            if (PiFound && !found)
                Offline?.Invoke(null, EventArgs.Empty);
            if (!PiFound && found)
                Online?.Invoke(null, EventArgs.Empty);

            PiFound = found;

            return PiFound;
        }

        /// <summary>
        /// Обновление и получение данных с сервера
        /// </summary>
        public static ApiResult<PiInfo> Update()
        {
            var result = ApiRequest("stats", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var stats = result.Json["stats"];
                var usedmem = stats["memory"]["used"].ToString();
                var totalmem = stats["memory"]["total"].ToString();
                var cputemp = stats["cpu"]["temperature"].ToString().Replace('.', ',');
                var cpuusg = stats["cpu"]["usage"].ToString().Replace('.', ',');
                var _gpios = JsonConvert.DeserializeObject<Dictionary<string, GPIOValue>>(stats["gpio"].ToString());
                var dht = JsonConvert.DeserializeObject<DHTInfo>(stats["external"].ToString());
                Dictionary<int, GPIOValue> gpios = new Dictionary<int, GPIOValue>();
                foreach (var _gpio in _gpios)
                {
                    gpios.Add(int.Parse(_gpio.Key), _gpio.Value);
                }

                Updated?.Invoke(null, EventArgs.Empty);
                return new PiInfo(float.Parse(cputemp), float.Parse(cpuusg), long.Parse(totalmem), float.Parse(usedmem), dht, gpios);
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }

        /// <summary>
        /// Выключение Raspberry Pi
        /// </summary>
        public static ApiResult<bool> Shutdown()
        {
            var result = ApiRequest("shutdown", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                return resp;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Перезагрузка Raspberry Pi
        /// </summary>
        public static ApiResult<bool> Reboot()
        {
            var result = ApiRequest("reboot", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                return resp;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Получение списка ботов
        /// </summary>
        public static ApiResult<IEnumerable<BotInfo>> GetBots()
        {
            var result = ApiRequest("bots", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            { 
                var resp = result.Json["bots"];
                var count = resp.Count();
                var childrens = resp.Children();
                var bots = childrens.Select(c => JsonConvert.DeserializeObject<BotInfo>(c.ToString())).ToArray();
            
                return bots;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Добавление бота
        /// </summary>
        public static ApiResult<BotInfo> AddBot(string name, string path, bool autorun = false)
        {
            var result = ApiRequest("bots", Method.POST, new BotInfo() { name = name, path = path, autorun = autorun });
            if (result.State < ApiStatus.Success)
                return result.State;

            if (result.Responce.StatusCode == (HttpStatusCode)400)
                return ApiStatus.Failed;

            try
            {
                var bot = JsonConvert.DeserializeObject<BotInfo>(result.Json["bot"].ToString());
                return bot;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Удаление бота
        /// </summary>
        public static ApiResult<bool> DeleteBot(int id)
        {
            var result = ApiRequest("bots/" + id.ToString(), Method.DELETE);
            if (result.State < ApiStatus.Success)
                return result.State;

            if (result.Responce.StatusCode == HttpStatusCode.NotFound)
                return ApiStatus.Failed;
            else
                return ApiStatus.Success;
        }


        /// <summary>
        /// Запуск бота
        /// </summary>
        public static ApiResult<bool> RunBot(int id)
        {
            var result = ApiRequest("bots/run/" + id.ToString(), Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                return resp;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Остановка бота
        /// </summary>
        public static ApiResult<bool> StopBot(int id)
        {
            var result = ApiRequest("bots/stop/" + id.ToString(), Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                return resp;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }

        /// <summary>
        /// Запуск сервиса Motion
        /// </summary>
        public static ApiResult<Uri> StartMotion()
        {
            var result = ApiRequest("motion/start", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            if (result.Responce.StatusCode != HttpStatusCode.Redirect)
                return ApiStatus.Failed;

            try
            {
                return new Uri(result.Responce.Headers.FirstOrDefault(h => h.Name == "Location").Value.ToString());
            }
            catch
            {
                return ApiStatus.Failed;
            }
        }
        /// <summary>
        /// Остановка сервиса Motion
        /// </summary>
        public static ApiResult<bool> StopMotion()
        {
            var result = ApiRequest("motion/stop", Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                return resp;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }

        /// <summary>
        /// Получение данных с пина
        /// </summary>
        public static ApiResult<PinInfo> GetPin(GPIONames Pin)
        {
            return GetPin((int)Pin);
        }
        /// <summary>
        /// Получение данных с пина
        /// </summary>
        public static ApiResult<PinInfo> GetPin(int Number)
        {
            var result = ApiRequest("gpio/" + Number.ToString(), Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                if (resp == true)
                {
                    var value = result.Json["value"].Value<int>();
                    return new ApiResult<PinInfo>(new PinInfo() { Direction = GPIODirection.Unknown, Resistor = GPIOResistor.Unknown, Value = (GPIOValue)value });
                }
                else
                    return ApiStatus.Failed;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Установка пина на ввод или вывод
        /// </summary>
        public static ApiResult<PinInfo> SetupPin(GPIONames Pin, PinInfo Value)
        {
            return SetupPin((int)Pin, Value);
        }
        /// <summary>
        /// Установка пина на ввод или вывод
        /// </summary>
        public static ApiResult<PinInfo> SetupPin(int Number, PinInfo Value)
        {
            var result = ApiRequest("gpio/" + Number.ToString(), Method.POST, Value);
            if (result.State < ApiStatus.Success)
                return result.State;

            if (result.Responce.StatusCode == (HttpStatusCode)400)
                return ApiStatus.Failed;

            try
            {
                var pin = JsonConvert.DeserializeObject<PinInfo>(result.Json["gpio"].ToString());
                return pin;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }
        /// <summary>
        /// Установка значения пина (+ или -)
        /// </summary>
        public static ApiResult<bool> SetPin(GPIONames Pin, GPIOValue Value)
        {
            return SetPin((int)Pin, Value);
        }
        /// <summary>
        /// Установка значения пина (+ или -)
        /// </summary>
        public static ApiResult<bool> SetPin(int Number, GPIOValue Value)
        {
            if (Value < 0)
                throw new ArgumentException("Value must be 0 or 1");

            var result = ApiRequest("gpio/" + Number.ToString() + "/" + (int)Value, Method.GET);
            if (result.State < ApiStatus.Success)
                return result.State;

            try
            {
                var resp = result.Json["result"].Value<bool>();
                if (result.Json["exception"] == null)
                    return resp;
                else
                    return ApiStatus.Failed;
            }
            catch
            {
                return ApiStatus.JsonUnexpected;
            }
        }

        /// <summary>
        /// Обращение к API Raspberry Pi
        /// </summary>
        private static ApiResponce ApiRequest(string request, Method method, object postdata = null)
        {
            if (CheckForPi())
            {
                Updating?.Invoke(null, new EventArgs());
                var req = new RestRequest(request, method);
                if (postdata != null)
                {
                    req.AddHeader("Content-type", "application/json");
                    req.AddJsonBody(postdata);
                }
                var resp = RestClient.Execute(req);
                if (resp.ContentType != "application/json")
                {
                    return new ApiResponce(resp, null);
                }
                try
                {
                    var json = JObject.Parse(resp.Content);
                    return new ApiResponce(resp, json);
                }
                catch(JsonReaderException e)
                {
                    return new ApiResponce(ApiStatus.JsonParsingError);
                }
            }

            return new ApiResponce(ApiStatus.PiNotFound);
        }
    }
}
