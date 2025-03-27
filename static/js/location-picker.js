/**
 * 位置选择器组件
 * 基于高德地图API，支持微信接口
 */
class LocationPicker {
    /**
     * 初始化位置选择器
     * @param {String} containerId 容器ID
     * @param {Object} options 配置项
     */
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.mapContainer = null;
        this.map = null;
        this.marker = null;
        this.geocoder = null;
        
        // 默认配置
        this.options = Object.assign({
            zoom: 13,
            center: [116.397428, 39.90923], // 默认北京
            markerDraggable: true,
            markerTitle: '选择位置',
            onSelect: null,
            useWechat: false,   // 是否使用微信获取位置
            apiKey: ''          // 高德地图API密钥
        }, options);
        
        this.latInput = null;
        this.lngInput = null;
        this.addressInput = null;
        
        // 检测是否在微信环境中
        this.isWechatBrowser = this.checkIsWechatBrowser();
        
        this.init();
    }
    
    /**
     * 检测是否在微信浏览器中
     */
    checkIsWechatBrowser() {
        return /MicroMessenger/i.test(navigator.userAgent);
    }
    
    /**
     * 初始化地图
     */
    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('找不到容器:', this.containerId);
            return;
        }
        
        // 创建地图容器
        this.mapContainer = document.createElement('div');
        this.mapContainer.className = 'location-map';
        this.mapContainer.style.height = '400px';
        this.mapContainer.style.marginBottom = '15px';
        container.appendChild(this.mapContainer);
        
        // 创建表单元素
        const formRow = document.createElement('div');
        formRow.className = 'row';
        
        // 创建经度输入框
        const lngCol = document.createElement('div');
        lngCol.className = 'col-md-3 mb-3';
        this.lngInput = document.createElement('input');
        this.lngInput.type = 'text';
        this.lngInput.className = 'form-control';
        this.lngInput.placeholder = '经度';
        this.lngInput.readOnly = true;
        const lngLabel = document.createElement('label');
        lngLabel.textContent = '经度';
        lngLabel.className = 'form-label';
        lngCol.appendChild(lngLabel);
        lngCol.appendChild(this.lngInput);
        
        // 创建纬度输入框
        const latCol = document.createElement('div');
        latCol.className = 'col-md-3 mb-3';
        this.latInput = document.createElement('input');
        this.latInput.type = 'text';
        this.latInput.className = 'form-control';
        this.latInput.placeholder = '纬度';
        this.latInput.readOnly = true;
        const latLabel = document.createElement('label');
        latLabel.textContent = '纬度';
        latLabel.className = 'form-label';
        latCol.appendChild(latLabel);
        latCol.appendChild(this.latInput);
        
        // 创建地址输入框
        const addressCol = document.createElement('div');
        addressCol.className = 'col-md-6 mb-3';
        this.addressInput = document.createElement('input');
        this.addressInput.type = 'text';
        this.addressInput.className = 'form-control';
        this.addressInput.placeholder = '地址';
        const addressLabel = document.createElement('label');
        addressLabel.textContent = '地址';
        addressLabel.className = 'form-label';
        addressCol.appendChild(addressLabel);
        addressCol.appendChild(this.addressInput);
        
        // 搜索按钮
        const searchBtn = document.createElement('button');
        searchBtn.type = 'button';
        searchBtn.className = 'btn btn-primary mt-2';
        searchBtn.textContent = '搜索地址';
        searchBtn.addEventListener('click', () => this.searchAddress());
        
        formRow.appendChild(lngCol);
        formRow.appendChild(latCol);
        formRow.appendChild(addressCol);
        container.appendChild(formRow);
        container.appendChild(searchBtn);
        
        // 创建获取当前位置按钮
        const btnRow = document.createElement('div');
        btnRow.className = 'row mt-2';
        
        // 获取当前位置按钮
        const getCurrentLocationBtn = document.createElement('button');
        getCurrentLocationBtn.type = 'button';
        getCurrentLocationBtn.className = 'btn btn-secondary me-2';
        getCurrentLocationBtn.textContent = '获取当前位置';
        getCurrentLocationBtn.addEventListener('click', () => this.getCurrentLocation());
        btnRow.appendChild(getCurrentLocationBtn);
        
        // 微信位置按钮（仅在微信浏览器中显示）
        if (this.isWechatBrowser || this.options.useWechat) {
            const getWechatLocationBtn = document.createElement('button');
            getWechatLocationBtn.type = 'button';
            getWechatLocationBtn.className = 'btn btn-success me-2';
            getWechatLocationBtn.textContent = '通过微信获取位置';
            getWechatLocationBtn.addEventListener('click', () => this.getWechatLocation());
            btnRow.appendChild(getWechatLocationBtn);
            
            // 如果设置了优先使用微信，先加载微信JS SDK
            if (this.options.useWechat) {
                this.loadWechatSDK();
            }
        }
        
        container.appendChild(btnRow);
        
        // 加载高德地图API
        this.loadMapAPI();
    }
    
    /**
     * 加载地图API
     */
    loadMapAPI() {
        if (window.AMap) {
            this.initMap();
            return;
        }
        
        const script = document.createElement('script');
        const apiKey = this.options.apiKey || '您的高德地图API密钥';
        script.src = `/static/vendor/amap/amap.js?v=2.0&key=${apiKey}`;
        script.onload = () => this.initMap();
        document.head.appendChild(script);
    }
    
    /**
     * 加载微信JS SDK
     */
    loadWechatSDK() {
        if (window.wx) {
            this.initWechat();
            return;
        }
        
        const script = document.createElement('script');
        script.src = '/static/vendor/wx/jweixin-1.6.0.js';
        script.onload = () => this.initWechat();
        document.head.appendChild(script);
    }
    
    /**
     * 初始化微信JS SDK
     */
    initWechat() {
        // 这里需要与后端配合，获取wx.config所需的参数
        // 通常需要向后端发起请求，获取必要的参数
        if (!window.wx) return;
        
        // 向后端请求微信JSSDK配置
        fetch('/api/wechat/jsconfig?url=' + encodeURIComponent(window.location.href))
            .then(response => response.json())
            .then(data => {
                window.wx.config({
                    debug: false,
                    appId: data.appId,
                    timestamp: data.timestamp,
                    nonceStr: data.nonceStr,
                    signature: data.signature,
                    jsApiList: ['getLocation', 'openLocation']
                });
                
                window.wx.ready(() => {
                    console.log('微信JSSDK初始化成功');
                });
                
                window.wx.error((err) => {
                    console.error('微信JSSDK初始化失败', err);
                });
            })
            .catch(error => {
                console.error('获取微信配置失败:', error);
            });
    }
    
    /**
     * 初始化地图
     */
    initMap() {
        // 创建地图实例
        this.map = new AMap.Map(this.mapContainer, {
            zoom: this.options.zoom,
            center: this.options.center
        });
        
        // 创建标记
        this.marker = new AMap.Marker({
            position: this.options.center,
            draggable: this.options.markerDraggable,
            title: this.options.markerTitle
        });
        
        this.marker.setMap(this.map);
        
        // 创建地理编码器
        this.geocoder = new AMap.Geocoder();
        
        // 监听地图点击事件
        this.map.on('click', (e) => {
            const lnglat = e.lnglat;
            this.updateMarker(lnglat);
            this.reverseGeocode(lnglat);
        });
        
        // 监听标记拖动事件
        this.marker.on('dragend', (e) => {
            const lnglat = this.marker.getPosition();
            this.updateInputs(lnglat);
            this.reverseGeocode(lnglat);
        });
        
        // 初始化输入框值
        this.updateInputs(this.options.center);
        this.reverseGeocode(this.options.center);
    }
    
    /**
     * 更新标记位置
     * @param {Array|Object} lnglat 经纬度
     */
    updateMarker(lnglat) {
        this.marker.setPosition(lnglat);
        this.map.setCenter(lnglat);
        this.updateInputs(lnglat);
    }
    
    /**
     * 更新输入框值
     * @param {Array|Object} lnglat 经纬度
     */
    updateInputs(lnglat) {
        if (Array.isArray(lnglat)) {
            this.lngInput.value = lnglat[0].toFixed(6);
            this.latInput.value = lnglat[1].toFixed(6);
        } else {
            this.lngInput.value = lnglat.lng.toFixed(6);
            this.latInput.value = lnglat.lat.toFixed(6);
        }
        
        // 回调选择事件
        if (typeof this.options.onSelect === 'function') {
            this.options.onSelect({
                lng: parseFloat(this.lngInput.value),
                lat: parseFloat(this.latInput.value),
                address: this.addressInput.value,
                source: 'map'  // 标记数据来源
            });
        }
    }
    
    /**
     * 反向地理编码
     * @param {Array|Object} lnglat 经纬度
     */
    reverseGeocode(lnglat) {
        this.geocoder.getAddress(lnglat, (status, result) => {
            if (status === 'complete' && result.info === 'OK') {
                this.addressInput.value = result.regeocode.formattedAddress;
                
                // 更新回调数据中的地址
                if (typeof this.options.onSelect === 'function') {
                    this.options.onSelect({
                        lng: parseFloat(this.lngInput.value),
                        lat: parseFloat(this.latInput.value),
                        address: this.addressInput.value,
                        source: 'geocode'  // 标记数据来源
                    });
                }
            } else {
                console.error('反向地理编码失败');
            }
        });
    }
    
    /**
     * 搜索地址
     */
    searchAddress() {
        const address = this.addressInput.value.trim();
        if (!address) {
            alert('请输入地址');
            return;
        }
        
        this.geocoder.getLocation(address, (status, result) => {
            if (status === 'complete' && result.info === 'OK') {
                const lnglat = result.geocodes[0].location;
                this.updateMarker(lnglat);
                this.map.setZoom(15);
            } else {
                alert('找不到该地址，请尝试更精确的地址');
            }
        });
    }
    
    /**
     * 获取当前位置（浏览器API）
     */
    getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lnglat = [position.coords.longitude, position.coords.latitude];
                    this.updateMarker(lnglat);
                    this.reverseGeocode(lnglat);
                },
                (error) => {
                    console.error('获取位置失败:', error);
                    alert('获取当前位置失败，请手动选择位置');
                }
            );
        } else {
            alert('您的浏览器不支持地理定位');
        }
    }
    
    /**
     * 通过微信获取位置
     */
    getWechatLocation() {
        if (!window.wx) {
            alert('微信SDK未加载，请刷新页面重试');
            return;
        }
        
        // 使用微信的地理位置API
        window.wx.getLocation({
            type: 'gcj02', // 使用gcj02坐标系（火星坐标，高德地图使用的坐标系）
            success: (res) => {
                // 微信返回的是gcj02坐标系，可以直接在高德地图中使用
                const lnglat = [res.longitude, res.latitude];
                this.updateMarker(lnglat);
                this.reverseGeocode(lnglat);
                
                // 标记位置来源
                if (typeof this.options.onSelect === 'function') {
                    this.options.onSelect({
                        lng: res.longitude,
                        lat: res.latitude,
                        address: this.addressInput.value,
                        source: 'wechat'  // 标记数据来源
                    });
                }
            },
            cancel: () => {
                // 用户取消授权
                alert('您已取消位置授权');
            },
            fail: (error) => {
                console.error('微信获取位置失败:', error);
                alert('通过微信获取位置失败，请允许位置权限或手动选择位置');
            }
        });
    }
    
    /**
     * 设置位置
     * @param {Object} location 位置对象，包含lng、lat属性
     */
    setLocation(location) {
        if (location && location.lng && location.lat) {
            const lnglat = [location.lng, location.lat];
            this.updateMarker(lnglat);
            this.reverseGeocode(lnglat);
        }
    }
    
    /**
     * 获取位置数据
     * @returns {Object} 位置数据，包含lng、lat、address属性
     */
    getLocation() {
        return {
            lng: parseFloat(this.lngInput.value),
            lat: parseFloat(this.latInput.value),
            address: this.addressInput.value
        };
    }
} 